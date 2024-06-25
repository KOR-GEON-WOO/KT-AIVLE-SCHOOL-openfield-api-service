from django.contrib import admin
from .models import *

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username',)
    readonly_fields = ('password',)

admin.site.register(CustomUser, CustomUserAdmin)