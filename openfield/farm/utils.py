from mySetting import NAVER_API_CLIENT_ID, NAVER_API_CLIENT_SECRET  
import requests

def get_satellite_image(x, y):
        url = 'https://naveropenapi.apigw.ntruss.com/map-static/v2/raster'
        headers = {
            'X-NCP-APIGW-API-KEY-ID': NAVER_API_CLIENT_ID,
            'X-NCP-APIGW-API-KEY': NAVER_API_CLIENT_SECRET,
        }
        params = {
            'center': f'{x},{y}',        # 중심 좌표
            'level': 18,                 # 줌 레벨
            'w': 512,                    # 이미지 가로 크기
            'h': 512,                    # 이미지 세로 크기
            'maptype': 'satellite_base', # 지도 유형: 위성 배경
            'scale': 1,                  # 해상도 스케일
            'crs': 'EPSG:4326',          # 좌표 체계: WGS84 경위도
            'format': 'jpg',             # 반환 이미지 형식: JPEG
            'public_transit': False,     # 대중교통 정보 제외
            'dataversion': '1.0'         # 데이터 버전
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.content
        else:
            error_msg = f"이미지를 다운로드하는 중 오류가 발생했습니다. 상태 코드: {response.status_code}, 응답: {response.text}"
            raise ValueError(error_msg)