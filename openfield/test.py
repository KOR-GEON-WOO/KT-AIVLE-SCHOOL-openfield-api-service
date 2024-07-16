import os
import django

# Django 설정 파일을 지정합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'openfield.settings')

# Django 환경을 초기화합니다.
django.setup()

# 이제 Django 모델을 임포트할 수 있습니다.
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Coalesce
from farm.models import Farm, FarmStatusLog, FarmIllegalBuildingLog

# 테스트 코드를 작성합니다.
def test_farm_model():
    queryset = Farm.objects.all().prefetch_related('status_logs')

    # 결과 출력 (테스트 코드)
    for farm in queryset:
        print(f'Farm ID: {farm.farm_id}, Owner: {farm.farm_owner}, Latest Status: {farm.status_logs}')

if __name__ == '__main__':
    test_farm_model()