from django.db import models
import uuid
import os
from datetime import datetime
from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
import boto3
import logging
logger = logging.getLogger(__name__)

def generate_farm_image_filename(instance, filename):
    extension = filename.split('.')[-1]
    date_str = datetime.now().strftime('%Y%m%d')
    new_filename = f"{uuid.uuid4()}_{date_str}.{extension}"
    return os.path.join('farm_image', new_filename)

class Farm(models.Model):
    farm_id = models.AutoField(primary_key=True)
    farm_owner = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    farm_name = models.CharField(max_length=255, default='Unknown')  
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  

    def __str__(self):
        return self.farm_owner

class FarmStatusLog(models.Model):
    farm_status_log_id = models.AutoField(primary_key=True)
    farm_status = models.IntegerField()
    farm_created = models.DateTimeField(auto_now_add=True)
    farm = models.ForeignKey(Farm, related_name='status_logs', on_delete=models.CASCADE)  # farm을 사용하는게 관례라고해서 수정 
    user_id = models.IntegerField()

    def __str__(self):
        return f"{self.farm} - Status {self.farm_status}"
    
class FarmImage(models.Model):
    farm = models.OneToOneField(Farm, related_name='image', on_delete=models.CASCADE)
    farm_image = models.ImageField(upload_to=generate_farm_image_filename, blank=True)

# S3에서 파일 삭제하는 함수
def delete_s3_file(file_name):
    try:
        s3 = boto3.client('s3',
                          aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                          region_name=settings.AWS_REGION)
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        s3.delete_object(Bucket=bucket, Key=file_name)
    except Exception as e:
        logger.error(f"Error deleting file from S3: {e}")

# S3에서 파일 삭제하는 신호 처리기 (삭제할 때)
@receiver(pre_delete, sender=FarmImage)
def delete_s3_file_on_delete(sender, instance, **kwargs):
    if instance.farm_image:
        delete_s3_file(instance.farm_image.name)

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