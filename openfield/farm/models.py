from django.db import models

class Farm(models.Model):
    farm_id = models.AutoField(primary_key=True)
    farm_owner = models.CharField(max_length=255)
    latitude = models.IntegerField()
    longitude = models.IntegerField()
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
