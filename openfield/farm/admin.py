from django.contrib import admin
from .models import Farm, FarmStatusLog, FarmImage, FarmPolygonDetectionImage, FarmIllegalBuildingLog, FarmChangeDetection ,FarmChangeDetectionLog 
from django.http import HttpResponseRedirect
from django import forms
from django.urls import path
from django.shortcuts import render
from django.contrib import messages
import csv
from .utils import csv_exception,read_csv_file,preprocess_dataframe,decode_raw_data,create_farm,create_farm_status_log,process_farm_images

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
            csv_file = csv_exception(self, request, csv_file)
            if csv_file is None:
                return HttpResponseRedirect(request.path_info)

            try:
                raw_data, encoding = read_csv_file(csv_file)
                df = preprocess_dataframe(csv_file, raw_data, encoding)
                file_data = decode_raw_data(raw_data, encoding)

                for row in csv.DictReader(file_data):
                    farm = create_farm(row)
                    create_farm_status_log(farm, 0, 1)
                    process_farm_images(self, request, farm, row)

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

@admin.register(FarmChangeDetection)
class FarmChangeDetectionAdmin(admin.ModelAdmin):
    list_display = ('farm', 'farm_change_detection_image','farm_change_detection_created')
    search_fields = ('farm__name',)

@admin.register(FarmChangeDetectionLog)
class FarmChangeDetectionLogAdmin(admin.ModelAdmin):
    list_display = ('farm', 'farm_change_detection_result_image1', 'farm_change_detection_result_image2','change_rating1','change_rating2','change_rating_result','farm_change_detection_log_created')
    search_fields = ('farm__name',)
    list_filter = ('change_rating_result',)
    