from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q
from django.db.models import OuterRef, Subquery
from datetime import datetime
from .models import Farm, FarmStatusLog
from .serializers import *
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import IsAuthenticated, IsAdminUser

# 페이지네이션 설정
class FarmPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 100
    
# 관리자 list view
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmAdminListAPIView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    
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

# 관리자 detail view
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmAdminDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdminUser]
    
    serializer_class = FarmDetailSerializer
    queryset = Farm.objects.filter(farmillegalbuildinglog__farm_illegal_building_status=0)

# 불법건축물 list view
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmIbDetectedListAPIView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    
    serializer_class = FarmListSerializer
    pagination_class = FarmPagination  # 페이지네이션 클래스 설정

    def get_queryset(self):
        queryset = Farm.objects.filter(farmillegalbuildinglog__farm_illegal_building_status=1)
        return queryset

# 불법건축물 detail view
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmIbDetectedDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdminUser]
    
    serializer_class = FarmPolygonDetectionDetailSerializer
    queryset = Farm.objects.filter(farmillegalbuildinglog__farm_illegal_building_status=1)

# 사용자 list view
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmUserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    
    serializer_class = FarmListSerializer
    def get_queryset(self):
        queryset = get_user_farms()
        return queryset

# 사용자 detail view
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmUserDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    
    # TODO: 고쳐야 할 수 있음 (admin과 동일)
    serializer_class = FarmDetailSerializer
    def get_queryset(self):
        queryset = get_user_farms()
        return queryset
    
# 사용자 mypage list view
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmUserMypageListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    
# 관리자 mypage list view
@method_decorator(ensure_csrf_cookie, name='dispatch')
class FarmAdminMypageListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    
def get_user_farms():
    latest_farm_status_log = FarmStatusLog.objects.filter(
        farm=OuterRef('pk')
    ).order_by('-farm_created').values('farm_status')[:1]

    # Step 2: 쿼리셋 구성
    # FarmIllegalBuildingLog에서 farm_illegal_building_status가 0인 Farm 객체를 가져옴
    queryset = Farm.objects.filter(
        farmillegalbuildinglog__farm_illegal_building_status=0
    ).annotate(
        latest_status=Subquery(latest_farm_status_log)
    ).filter(
        latest_status=1
    )
    
    return queryset