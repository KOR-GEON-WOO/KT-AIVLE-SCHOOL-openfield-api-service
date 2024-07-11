from rest_framework import serializers
from .models import *

class FarmListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = '__all__'

class FarmStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmStatusLog
        fields = ['farm_status_log_id', 'farm_status', 'farm_created', 'user_id']

class FarmIllegalBuildingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmIllegalBuildingLog
        fields = ['farm_illegal_building_status', 'farm_ib_log_created']

class FarmImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmImage
        fields = ['farm_image']

class FarmPolygonDetectionImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmPolygonDetectionImage
        fields = ['farm_pd_image']

class FarmDetailSerializer(serializers.ModelSerializer):
    status_logs = FarmStatusLogSerializer(many=True, read_only=True)
    image = FarmImageSerializer(read_only=True)
    
    class Meta:
        model = Farm
        fields = '__all__'

class FarmPolygonDetectionDetailSerializer(serializers.ModelSerializer):
    status_logs = FarmStatusLogSerializer(many=True, read_only=True)
    illegal_logs = FarmIllegalBuildingLogSerializer(many=True, read_only=True)
    pd_image = FarmPolygonDetectionImageSerializer(read_only=True)
    
    class Meta:
        model = Farm
        fields = '__all__'