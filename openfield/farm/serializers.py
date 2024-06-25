from rest_framework import serializers
from .models import Farm, FarmStatusLog

class FarmListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = '__all__'

class FarmStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmStatusLog
        fields = ['farm_status_log_id', 'farm_status', 'farm_created', 'user_id']

class FarmDetailSerializer(serializers.ModelSerializer):
    status_logs = FarmStatusLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Farm
        fields = '__all__'
