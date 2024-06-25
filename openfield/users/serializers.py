from rest_framework import serializers
from .models import CustomUser
from datetime import datetime

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    birthday = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'confirm_password', 'user_realname', 'birthday']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        
        if 'birthday' in data:
            try:
                birthday = datetime.strptime(data['birthday'], '%Y%m%d').date()
                data['birthday'] = birthday.strftime('%Y-%m-%d')
            except ValueError:
                raise serializers.ValidationError("Incorrect date format. Use 'YYYYMMDD' format.")
        
        return data
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        birthday = validated_data.pop('birthday')
        
        user = CustomUser(
            username=validated_data['username'],
            user_realname=validated_data['user_realname'],
            birthday=birthday  #ISO 8601
        )
        user.set_password(password)
        user.save()
        return user
