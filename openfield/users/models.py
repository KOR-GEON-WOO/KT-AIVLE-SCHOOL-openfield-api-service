from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    # 추가 필드 정의 (옵션)
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.username
