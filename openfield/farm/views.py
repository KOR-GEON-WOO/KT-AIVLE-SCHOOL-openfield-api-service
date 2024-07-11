from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q
from datetime import datetime
from .models import Farm, FarmStatusLog
from .serializers import *
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import IsAuthenticated

# 페이지네이션 설정
class FarmPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 100
    
# Farm 모델의 데이터를 리스트 조회하는 view
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    
    serializer_class = FarmListSerializer
    pagination_class = FarmPagination  # 페이지네이션 클래스 설정

    def get_queryset(self):
        queryset = Farm.objects.filter(farmillegalbuildinglog__farm_illegal_building_status=0)

        # farm_created 필터링 기준으로 받기
        farm_created_param = self.request.query_params.get('farm_created', None)
        if farm_created_param:
            try:
                farm_created_date = datetime.strptime(farm_created_param, '%Y%m%d').date()
                # farm_created_date를 기준으로 필터링
                queryset = queryset.filter(
                    status_logs__farm_created__date__gte=farm_created_date
                ).distinct()
            except ValueError:
                # 날짜 형식이 올바르지 않은 경우 처리
                queryset = Farm.objects.none()  # 빈 쿼리셋 반환

        return queryset

# Farm 모델
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    
    serializer_class = FarmDetailSerializer
    queryset = Farm.objects.filter(farmillegalbuildinglog__farm_illegal_building_status=0)
    
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmIbDetectedListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    
    serializer_class = FarmListSerializer
    pagination_class = FarmPagination  # 페이지네이션 클래스 설정

    def get_queryset(self):
        queryset = Farm.objects.filter(farmillegalbuildinglog__farm_illegal_building_status=1)
        return queryset
        
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmIbDetectedDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    
    serializer_class = FarmPolygonDetectionDetailSerializer
    queryset = Farm.objects.filter(farmillegalbuildinglog__farm_illegal_building_status=1)
