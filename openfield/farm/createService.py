from mySetting import NAVER_API_CLIENT_ID, NAVER_API_CLIENT_SECRET  
import requests
import uuid
import os
from datetime import datetime
from PIL import Image,UnidentifiedImageError,ImageDraw
from django.conf import settings
from django.contrib import messages
from decimal import Decimal
from io import BytesIO
from django.core.files.base import ContentFile
import numpy as np
import cv2
from .models import *
from .utils import string_to_polygon,make_result_df,point_in_polygon,function

def generate_farm_image_filename(instance, filename):  # 생성한 파일 이름을 기반으로 S3 저장
    new_filename = generate_filename(filename)
    return os.path.join('farm_image', new_filename)

def generate_filename(filename):                      # uuid 를 사용해 파일이름 생성 
    extension = filename.split('.')[-1]
    date_str = datetime.now().strftime('%Y%m%d')
    new_filename = f"{uuid.uuid4()}_{date_str}.{extension}"
    return new_filename

def get_satellite_image(x, y):      # 네이버 지도 api 
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

def create_farm(row):                                # farm 생성하기 
    from .models import Farm  # 지연 로딩
    farm_owner = row.get('지목') # 100_land.csv 올려서 수정함
    latitude = float(row.get('위도', 0.0))
    longitude = float(row.get('경도', 0.0))
    farm_name = row.get('주소', 'Unknown')
    farm_size = Decimal(row.get('토지면적', 0.0))
    farm_geometry = string_to_polygon(row.get('geometry'))

    return Farm.objects.create(
        farm_owner=farm_owner,
        latitude=latitude,
        longitude=longitude,
        farm_name=farm_name,
        farm_size=farm_size,
        farm_geometry=farm_geometry,
    )

def create_farm_status_log(farm, row):             # farm log 생성하기 
    from .models import FarmStatusLog  # 지연 로딩
    farm_status = int(row.get('상태', 1))
    user_id = int(row.get('사용자', 1))
    FarmStatusLog.objects.create(
        farm=farm,
        farm_status=farm_status,
        user_id=user_id,
    )

def process_farm_images(self, request, farm, row):       # farm image 생성하기 및 그림 그리기 
    from .models import FarmImage # 지연 로딩
    try:
        polygon = function(farm.latitude, farm.longitude, farm.farm_geometry)
        image_content = get_satellite_image(farm.longitude, farm.latitude)
        image = Image.open(BytesIO(image_content))
        image_content = polygon_draw_image(image_content,polygon) # polygon
        
        FarmImage.objects.create(
            farm=farm,
            farm_image=ContentFile(image_content, f"farm_image_{farm.farm_id}.jpg")
        )
        model_result_df = make_result_df(image)
        model_result_df['inside_polygon'] = None

        image = draw_detected_objects(image, model_result_df, polygon, farm)
        polygon_draw=polygon_draw_image(image,polygon)  # polygon
        save_farm_polygon_image(polygon_draw, farm)

    except UnidentifiedImageError:
        self.message_user(request, "이미지를 열 수 없습니다. 파일이 손상되었거나 지원되지 않는 형식일 수 있습니다.", level=messages.ERROR)
    except Exception as e:
        self.message_user(request, f"이미지 처리 중 오류 발생: {e}", level=messages.ERROR)

def draw_detected_objects(image, model_result_df, polygon, farm):           # 불법 건축물 그리기 
    from .models import FarmIllegalBuildingLog  # 지연 로딩
    image = np.array(image)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cnt = 0
    for i, df_row in model_result_df.iterrows():
        if point_in_polygon(df_row['x'], df_row['y'], polygon):
            draw_rectangle(image, df_row, font)
            cnt = update_farm_illegal_building_log(df_row, farm, cnt)
    if cnt == 0:
        FarmIllegalBuildingLog.objects.create(farm=farm, farm_illegal_building_status=0)
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

def draw_rectangle(image, df_row, font):        # 사각형 그리기 
    top_left = (int(df_row['x'] - df_row['width'] / 2), int(df_row['y'] - df_row['height'] / 2))
    top_left_text = (int(df_row['x'] - df_row['width'] / 2), int(df_row['y'] - df_row['height'] / 2) - 6)
    bottom_right = (int(df_row['x'] + df_row['width'] / 2), int(df_row['y'] + df_row['height'] / 2))
    
    colors = {0: (0, 0, 255), 1: (255, 0, 0), 2: (0, 255, 0)}
    color = colors.get(df_row['class'], (0, 0, 0))
    cv2.rectangle(image, top_left, bottom_right, color, 3)
    cv2.putText(image, str(round(df_row['conf'], 2)), top_left_text, font, 0.5, color, 1, cv2.LINE_AA)

def update_farm_illegal_building_log(df_row, farm, cnt):           # 불법 건축물 log 생성 
    from .models import FarmIllegalBuildingLog  # 지연 로딩
    if df_row['class'] == 0 and cnt == 0:
        FarmIllegalBuildingLog.objects.create(farm=farm, farm_illegal_building_status=1)
        cnt = 1
    return cnt

def save_farm_polygon_image(image_bytes, farm):                 # 불법 건축물 이미지 생성 
    from .models import FarmPolygonDetectionImage  # 지연 로딩
    image = Image.open(BytesIO(image_bytes))
    output = BytesIO()
    image.save(output, format='JPEG')
    new_filename = f"{farm.farm_id}_{datetime.now().strftime('%Y%m%d')}.jpg"
    # TODO: 여기 이미지 저장 
    FarmPolygonDetectionImage.objects.create(
        farm=farm,
        farm_pd_image=ContentFile(output.getvalue(), new_filename)
    )
    output.close()

def polygon_draw_image(image, polygon,):       
    if isinstance(image, bytes):
        image_bytes = BytesIO(image)
        satellite_image = Image.open(image_bytes)
    else:
        satellite_image = image
    polygon_coords = list(polygon.exterior.coords)
    draw = ImageDraw.Draw(satellite_image)
    line_width = 1       # 라인 두께를 지정합니다
     
    for i in range(len(polygon_coords)):
        start_point = polygon_coords[i]
        end_point = polygon_coords[(i + 1) % len(polygon_coords)]
        draw.line([start_point, end_point], fill="yellow", width=line_width)
 
    output_bytes = BytesIO()
    satellite_image.save(output_bytes, format='PNG')
    output_bytes.seek(0)
    original_image_bytes = output_bytes.getvalue()
 
    return original_image_bytes
