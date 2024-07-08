from rest_framework import serializers
from .models import Farm, FarmStatusLog, FarmImage

class FarmListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = '__all__'

class FarmStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmStatusLog
        fields = ['farm_status_log_id', 'farm_status', 'farm_created', 'user_id']

class FarmImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmImage
        fields = ['farm_image']
# TODO: 객체탐지 및 폴리곤탐지 serializer 추가
class FarmDetailSerializer(serializers.ModelSerializer):
    status_logs = FarmStatusLogSerializer(many=True, read_only=True)
    image = FarmImageSerializer(read_only=True)
    
    class Meta:
        model = Farm
        fields = '__all__'
