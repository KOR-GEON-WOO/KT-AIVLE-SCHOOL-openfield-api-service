from django.db import models
from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
import logging
from .utils import delete_s3_file, generate_farm_image_filename
logger = logging.getLogger(__name__)

class Farm(models.Model):
    farm_id = models.AutoField(primary_key=True)
    farm_owner = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    farm_name = models.CharField(max_length=255, default='Unknown')  
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  
    farm_geometry = models.CharField(max_length=255 ,default='') # 폴리곤 객체를 넣을거면 포스트큐엘 쓰라고 해서 string 넣음
    
    def __str__(self):
        return str(self.farm_id)

class FarmStatusLog(models.Model):
    farm_status_log_id = models.AutoField(primary_key=True)
    farm_status = models.IntegerField()
    farm_created = models.DateTimeField(auto_now_add=True)
    farm = models.ForeignKey(Farm, related_name='status_logs', on_delete=models.CASCADE)  # farm을 사용하는게 관례라고해서 수정 
    user_id = models.IntegerField()

    def __str__(self):
        return f"{self.farm} - Status {self.farm_status}"
    
class FarmIllegalBuildingLog(models.Model):
    farm = models.OneToOneField(Farm, on_delete=models.CASCADE)
    farm_illegal_building_log_id=models.AutoField(primary_key=True)
    farm_illegal_building_status=models.IntegerField()
    farm_ib_log_created = models.DateTimeField(auto_now_add=True)
    
class FarmImage(models.Model):
    farm = models.OneToOneField(Farm, related_name='image', on_delete=models.CASCADE)
    farm_image = models.ImageField(upload_to=generate_farm_image_filename, blank=True)

# TODO: Object detection 결과 (x, y좌표와 레이블 값이 담긴 text) 컬럼 필요
# x, y, conf, class 어떻게 저장해야할까
class FarmObjectDetectionImage(models.Model):
    farm = models.ForeignKey(Farm, related_name='od_image', on_delete=models.CASCADE)
    farm_object_x = models.FloatField()
    farm_object_y = models.FloatField()
    farm_object_conf=models.FloatField()
    farm_object_class_id= models.IntegerField()
    farm_boxes_num_elemnets=models.IntegerField()
    farm_Detection_image=models.ImageField(upload_to=generate_farm_image_filename,blank=True)


class FarmPolygonDetectionImage(models.Model):
    farm = models.OneToOneField(Farm, related_name='pd_image', on_delete=models.CASCADE)
    farm_pd_image = models.ImageField(upload_to=generate_farm_image_filename,blank=True)

class FarmChangeDetection(models.Model):
    farm = models.ForeignKey(Farm, related_name='cd',on_delete=models.CASCADE)
    farm_change_detection_image = models.ImageField(upload_to=generate_farm_image_filename,blank=True)
    farm_change_detection_created = models.DateTimeField(auto_now_add=True)
    
class FarmChangeDetectionLog(models.Model):
    farm=models.ForeignKey(Farm,related_name='cd_log',on_delete=models.CASCADE)
    farm_change_detection_result_image1=models.ImageField(upload_to=generate_farm_image_filename,blank=True)
    farm_change_detection_result_image2=models.ImageField(upload_to=generate_farm_image_filename,blank=True)
    change_rating1 = models.FloatField()
    change_rating2 = models.FloatField()
    change_rating_result = models.FloatField()

    
# S3에서 파일 삭제하는 신호 처리기 (삭제할 때)
@receiver(pre_delete, sender=FarmChangeDetection)
def delete_s3_file_on_delete(sender, instance, **kwargs):
    if instance.farm_change_detection_image:
        delete_s3_file(instance.farm_change_detection_image.name)

# S3에서 파일 삭제하는 신호 처리기 (삭제할 때)
@receiver(pre_delete, sender=FarmChangeDetectionLog)
def delete_s3_file_on_delete(sender, instance, **kwargs):
    if instance.farm_change_detection_result_image1 and instance.farm_change_detection_result_image2:
        delete_s3_file(instance.farm_change_detection_result_image1.name)
        delete_s3_file(instance.farm_change_detection_result_image2.name)

# S3에서 파일 삭제하는 신호 처리기 (삭제할 때)
@receiver(pre_delete, sender=FarmImage)
def delete_s3_file_on_delete(sender, instance, **kwargs):
    if instance.farm_image:
        delete_s3_file(instance.farm_image.name)

# S3에서 파일 삭제하는 신호 처리기 (삭제할 때)
@receiver(pre_delete, sender=FarmPolygonDetectionImage)
def delete_s3_file_on_delete(sender, instance, **kwargs):
    if instance.farm_pd_image:
        delete_s3_file(instance.farm_pd_image.name)

# S3에서 파일 삭제하는 신호 처리기 (이미지 필드를 비울 때)
@receiver(pre_save, sender=FarmImage)
def delete_s3_file_on_clear(sender, instance, **kwargs):
    if not instance.pk:
        return False  # 새 객체인 경우 무시

    try:
        old_instance = FarmImage.objects.get(pk=instance.pk)
    except FarmImage.DoesNotExist:
        return False

    old_file = old_instance.farm_image
    new_file = instance.farm_image

    if not new_file and old_file:  # 이미지가 비워질 때
        delete_s3_file(old_file.name)
        
# S3에서 파일 삭제하는 신호 처리기 (이미지 필드를 비울 때)
@receiver(pre_save, sender=FarmPolygonDetectionImage)
def delete_s3_file_on_clear(sender, instance, **kwargs):
    if not instance.pk:
        return False  # 새 객체인 경우 무시

    try:
        old_instance = FarmPolygonDetectionImage.objects.get(pk=instance.pk)
    except FarmPolygonDetectionImage.DoesNotExist:
        return False

    old_file = old_instance.farm_pd_image
    new_file = instance.farm_pd_image

    if not new_file and old_file:  # 이미지가 비워질 때
        delete_s3_file(old_file.name)

# S3에서 파일 삭제하는 신호 처리기 (이미지 필드를 비울 때)
@receiver(pre_save, sender=FarmChangeDetection)
def delete_s3_file_on_clear(sender, instance, **kwargs):
    if not instance.pk:
        return False  # 새 객체인 경우 무시
    try:
        old_instance = FarmChangeDetection.objects.get(pk=instance.pk)
    except FarmChangeDetection.DoesNotExist:
        return False

    old_file = old_instance.farm_change_detection_image
    new_file = instance.farm_change_detection_image

    if not new_file and old_file:  # 이미지가 비워질 때
        delete_s3_file(old_file.name)

# S3에서 파일 삭제하는 신호 처리기 (이미지 필드를 비울 때)
@receiver(pre_save, sender=FarmChangeDetectionLog)
def delete_s3_file_on_clear(sender, instance, **kwargs):
    if not instance.pk:
        return False  # 새 객체인 경우 무시
    try:
        old_instance = FarmChangeDetectionLog.objects.get(pk=instance.pk)
    except FarmChangeDetectionLog.DoesNotExist:
        return False

    old_file1 = old_instance.farm_change_detection_result_image1
    new_file1 = instance.farm_change_detection_result_image1

    old_file2 = old_instance.farm_change_detection_result_image2
    new_file2 = instance.farm_change_detection_result_image2

    # Check and delete the first image if it's being cleared
    if not new_file1 and old_file1:
        delete_s3_file(old_file1.name)

    # Check and delete the second image if it's being cleared
    if not new_file2 and old_file2:
        delete_s3_file(old_file2.name)