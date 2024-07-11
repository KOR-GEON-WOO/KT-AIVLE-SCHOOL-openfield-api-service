from django.contrib import admin
from .models import Farm, FarmStatusLog, FarmImage, FarmPolygonDetectionImage, FarmIllegalBuildingLog
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
from PIL import Image, UnidentifiedImageError, ImageDraw,ImageFont
from io import BytesIO
import pandas as pd
from shapely.geometry import Polygon
from .utils import get_satellite_image, string_to_polygon, polygon_function, make_result_df, point_in_polygon,csv_exception
import cv2
import numpy as np
class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()

class FarmStatusLogInline(admin.TabularInline):
    model = FarmStatusLog
    extra = 0

class FarmImageInline(admin.TabularInline):
    model = FarmImage
    extra = 0

class FarmPolygonDetectionImageInline(admin.TabularInline):
    model = FarmPolygonDetectionImage
    extra = 0
class FarmIllegalBuildingLogInline(admin.TabularInline):
    model=FarmIllegalBuildingLog
    extra=0

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('farm_id', 'farm_owner', 'latitude', 'longitude', 'farm_name', 'farm_size')
    inlines = [FarmStatusLogInline, FarmImageInline, FarmPolygonDetectionImageInline,FarmIllegalBuildingLogInline,]
    change_list_template = "admin/farm_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-csv/', self.upload_csv)
        ]
        return custom_urls + urls

    def upload_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            csv_file = csv_exception(self,request, csv_file) 
            if csv_file is None: 
                return HttpResponseRedirect(request.path_info)

            try:
                raw_data = csv_file.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] if result['encoding'] is not None else 'utf-8'

                csv_file.seek(0)  # 파일 포인터를 처음으로 되돌림
                df = pd.read_csv(BytesIO(raw_data), encoding=encoding)
                df['geometry'] = df['geometry'].apply(string_to_polygon)
                df['pixel_polygon'] = df.apply(lambda row: polygon_function(row['위도'], row['경도'], row['geometry']), axis=1)

                file_data = raw_data.decode(encoding).splitlines()
                csv_reader = csv.DictReader(file_data)
                for row in csv_reader:
                    farm_owner = row.get('소유구분')
                    latitude = float(row.get('위도', 0.0))
                    longitude = float(row.get('경도', 0.0))
                    farm_name = row.get('주소', 'Unknown')
                    farm_size = Decimal(row.get('토지면적', 0.0))
                    farm_geometry = string_to_polygon(row.get('geometry'))  # 변경

                    farm = Farm.objects.create(
                        farm_owner=farm_owner,
                        latitude=latitude,
                        longitude=longitude,
                        farm_name=farm_name,
                        farm_size=farm_size,
                        farm_geometry=farm_geometry,
                    )

                    farm_status = int(row.get('상태', 1))
                    user_id = int(row.get('사용자', 1))
                    FarmStatusLog.objects.create(
                        farm=farm,
                        farm_status=farm_status,
                        user_id=user_id,
                    )

                    try:
                        
                        # FarmImage 모델에 이미지 저장
                        image_content = get_satellite_image(longitude, latitude)
                        image = Image.open(BytesIO(image_content))  # 여기 수정 
                        
                        farm_image = FarmImage.objects.create(
                            farm=farm,
                            farm_image=ContentFile(image_content, f"farm_image_{farm.farm_id}.jpg")
                        )

                        # FarmPolygonDetectionImage 모델에 이미지 저장
                        polygon = polygon_function(latitude, longitude, farm_geometry)
                        model_result_df = make_result_df(image)
                        model_result_df['inside_polygon'] = None

                        # 이미지에 그리기
                        image = np.array(image)  # PIL 이미지에서 numpy 배열로 변환
                        font = cv2.FONT_HERSHEY_SIMPLEX  # OpenCV 폰트 설정

                        cnt=0
                        for i, df_row in model_result_df.iterrows():
                            check = point_in_polygon(df_row['x'], df_row['y'], polygon)
                            if check:
                                top_left = (int(df_row['x'] - df_row['width'] / 2), int(df_row['y'] - df_row['height'] / 2))
                                top_left_text=(int(df_row['x'] - df_row['width'] / 2), int(df_row['y'] - df_row['height'] / 2)-6)
                                bottom_right = (int(df_row['x'] + df_row['width'] / 2), int(df_row['y'] + df_row['height'] / 2))

                                if df_row['class'] == 0:  # 건물
                                    cv2.rectangle(image, top_left, bottom_right, (0, 0, 255), 3)  # 빨간색 사각형
                                    cv2.putText(image, str(round(df_row['conf'], 2)), top_left_text, font, 0.5, (0, 0, 255), 1, cv2.LINE_AA)  # 빨간색 텍스트
                                    if cnt == 0:
                                        FarmIllegalBuildingLog.objects.create(
                                            farm=farm,
                                            farm_illegal_building_status=1,
                                        )
                                        cnt=1
                                elif df_row['class'] == 1:  # 태양광
                                    cv2.rectangle(image, top_left, bottom_right, (255, 0, 0), 3)  # 파란색 사각형
                                    cv2.putText(image, str(round(df_row['conf'], 2)), top_left_text, font, 0.5, (255, 0, 0), 1, cv2.LINE_AA)  # 파란색 텍스트
                                
                                elif df_row['class'] == 2:  # 비닐하우스
                                    cv2.rectangle(image, top_left, bottom_right, (0, 255, 0), 3)  # 초록색 사각형
                                    cv2.putText(image, str(round(df_row['conf'], 2)), top_left_text, font, 0.5, (0, 255, 0), 1, cv2.LINE_AA)  # 초록색 텍스트
                        if cnt == 0:
                            FarmIllegalBuildingLog.objects.create(
                                farm=farm,
                                farm_illegal_building_status=0,
                            )    
                        # 이미지 포맷을 명시적으로 지정하고 저장
                        image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))  # numpy 배열을 PIL 이미지로 변환
                        output = BytesIO()
                        image_pil.save(output, format='JPEG')  # JPEG 포맷으로 저장
                        new_filename = f"{farm.farm_id}_{datetime.now().strftime('%Y%m%d')}.jpg"
                        farm_polygon_image = FarmPolygonDetectionImage.objects.create(
                            farm=farm,
                            farm_pd_image=ContentFile(output.getvalue(), new_filename)
                        )
                        output.close()

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

@admin.register(FarmPolygonDetectionImage)
class FarmPolygonDetectionImageAdmin(admin.ModelAdmin):
    list_display = ('farm', 'farm_pd_image_url')

    def farm_pd_image_url(self, obj):
        return obj.farm_pd_image.url if obj.farm_pd_image else '-'

    farm_pd_image_url.short_description = 'Farm Polygon Detection Image URL'
    
@admin.register(FarmIllegalBuildingLog)
class FarmIllgalBuildingLogAdmin(admin.ModelAdmin):
    list_display = ('farm', 'farm_illegal_building_status')
    