from rest_framework import serializers
from .models import Farm, FarmStatusLog

class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = '__all__'

class FarmStatusLogSerializer(serializers.ModelSerializer):
    farm = FarmSerializer()

    class Meta:
        model = FarmStatusLog
        fields = ['farm_status_log_id', 'farm_status', 'farm_created', 'farm', 'user_id']
