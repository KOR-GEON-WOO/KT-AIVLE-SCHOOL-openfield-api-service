from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.conf import settings

class UserCreateAPIView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserLoginAPIView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        # 사용자 인증
        user = authenticate(username=username, password=password)
        if user:
            # 사용자가 존재하면 토큰 생성
            token, created = Token.objects.get_or_create(user=user)
             # 토큰을 쿠키에 저장
            response = Response({'token': token.key}, status=status.HTTP_200_OK)
            expiry = timezone.now() + settings.AUTH_TOKEN_EXPIRY 
            response.set_cookie(key='auth_token', value=token.key, expires=expiry)
            
            return response        
        else:
            # 사용자가 존재하지 않으면 인증 실패 메시지 반환
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class UserLogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능하도록 설정

    def post(self, request):
       if request.method == 'POST':
        try:
            request.user.auth_token.delete()
            return Response({'detail': '사용자의 로그아웃이 완료되었습니다.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)