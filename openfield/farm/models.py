from django.db import models

class Farm(models.Model):
    farm_id = models.CharField(max_length=255, primary_key=True)
    farm_owner = models.CharField(max_length=255)
    latitude = models.IntegerField()
    longitude = models.IntegerField()

    def __str__(self):
        return self.farm_id
