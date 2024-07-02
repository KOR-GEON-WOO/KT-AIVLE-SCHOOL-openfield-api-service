from django.contrib import admin
from .models import *

class FarmAdmin(admin.ModelAdmin):
    list_display = ('farm_id',)
    
    class FarmStatusLogInline(admin.TabularInline):
        model = FarmStatusLog
        extra = 0
        
    inlines = [FarmStatusLogInline]
    
    
class FarmStatusLogAdmin(admin.ModelAdmin):
    list_display = ('farm_status_log_id', 'farm', 'farm_status', 'farm_created','farm_image',)
    list_filter = ('farm_status', 'farm_created')
    search_fields = ('farm__farm_owner',)

admin.site.register(Farm, FarmAdmin)
admin.site.register(FarmStatusLog, FarmStatusLogAdmin)
