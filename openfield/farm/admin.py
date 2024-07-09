from django.contrib import admin
from .models import Farm, FarmStatusLog, FarmImage
from django.http import HttpResponseRedirect
from decimal import Decimal
from django import forms
from django.urls import path
from django.shortcuts import render
from django.contrib import messages
import csv
import chardet
from datetime import datetime
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from .utils import get_satellite_image

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()

class FarmStatusLogInline(admin.TabularInline):
    model = FarmStatusLog
    extra = 0

class FarmImageInline(admin.TabularInline):
    model = FarmImage
    extra = 0

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('farm_id', 'farm_owner', 'latitude', 'longitude', 'farm_name', 'farm_size')
    inlines = [FarmStatusLogInline, FarmImageInline]
    change_list_template = "admin/farm_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.upload_csv)
        ]
        return custom_urls + urls

    # TODO: utils의 detection 함수 사용해서 결과 저장
    def upload_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                self.message_user(request, "CSV 파일을 선택해 주세요", level=messages.ERROR)
                return HttpResponseRedirect(request.path_info)
            if not csv_file.name.endswith('.csv'):
                self.message_user(request, "CSV 파일이 아닙니다", level=messages.ERROR)
                return HttpResponseRedirect(request.path_info)

            raw_data = csv_file.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['encoding'] is not None else 'utf-8'

            try:
                file_data = raw_data.decode(encoding).splitlines()
                csv_reader = csv.DictReader(file_data)
                for row in csv_reader:
                    farm_owner = row.get('소유구분')
                    latitude = float(row.get('위도', 0.0))
                    longitude = float(row.get('경도', 0.0))
                    farm_name = row.get('주소', 'Unknown')
                    farm_size = Decimal(row.get('토지면적', 0.0))

                    farm = Farm.objects.create(
                        farm_owner=farm_owner,
                        latitude=latitude,
                        longitude=longitude,
                        farm_name=farm_name,
                        farm_size=farm_size,
                    )

                    farm_status = int(row.get('상태', 1))
                    user_id = int(row.get('사용자', 1))
                    FarmStatusLog.objects.create(
                        farm=farm,
                        farm_status=farm_status,
                        user_id=user_id,
                    )

                    try:
                        image_content = get_satellite_image(longitude,latitude)
                        try:
                            image = Image.open(BytesIO(image_content))
                            image_format = image.format  # 이미지의 포맷 가져오기
                        except UnidentifiedImageError:
                            image_format = None

                        if image_format not in ['JPEG', 'PNG']:
                            raise ValueError("지원하지 않는 이미지 포맷입니다.")

                        farm_image = FarmImage.objects.create(farm=farm)

                        extension = image_format.lower() if image_format else 'png'  # 이미지 확장자
                        date_str = datetime.now().strftime('%Y%m%d')
                        new_filename = f"{farm.farm_id}_{date_str}.{extension}"

                        farm_image.farm_image.save(new_filename, ContentFile(image_content))
                    except UnidentifiedImageError:
                        self.message_user(request, "이미지를 열 수 없습니다. 파일이 손상되었거나 지원되지 않는 형식일 수 있습니다.", level=messages.ERROR)
                    except Exception as e:
                        self.message_user(request, f"이미지 처리 중 오류 발생: {e}", level=messages.ERROR)

                self.message_user(request, "CSV 파일 업로드 성공!", level=messages.SUCCESS)
                return HttpResponseRedirect("../")
            except Exception as e:
                self.message_user(request, f"파일 처리 중 오류 발생: {e}", level=messages.ERROR)
                return HttpResponseRedirect(request.path_info)

        form = CSVUploadForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)

@admin.register(FarmStatusLog)
class FarmStatusLogAdmin(admin.ModelAdmin):
    list_display = ('farm_status_log_id', 'farm', 'farm_status', 'farm_created')
    list_filter = ('farm_status', 'farm_created')
    search_fields = ('farm__farm_owner',)

@admin.register(FarmImage)
class FarmImageAdmin(admin.ModelAdmin):
    list_display = ('farm', 'farm_image_url')

    def farm_image_url(self, obj):
        return obj.farm_image.url if obj.farm_image else '-'

    farm_image_url.short_description = 'Farm Image URL'
