from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True)
    birthday = models.DateField(null=False, blank=False, default=date.today)
    user_realname = models.CharField(null=False, blank=False, max_length=150)

    def __str__(self):
        return self.username
