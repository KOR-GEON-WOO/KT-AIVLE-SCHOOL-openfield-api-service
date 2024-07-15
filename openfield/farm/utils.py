from rest_framework.response import Response
from mySetting import NAVER_API_CLIENT_ID, NAVER_API_CLIENT_SECRET  
import requests
import boto3
import logging
import uuid
import os
from datetime import datetime
from django.conf import settings
from django.contrib import messages
from PIL import Image,UnidentifiedImageError
from ultralytics import YOLO
from pyproj import Transformer
import math
from shapely.geometry import Polygon, Point
import pandas as pd
import chardet
from decimal import Decimal
from io import BytesIO
from django.core.files.base import ContentFile
import numpy as np
import cv2

logger = logging.getLogger(__name__)

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

def generate_farm_image_filename(instance, filename):
    extension = filename.split('.')[-1]
    date_str = datetime.now().strftime('%Y%m%d')
    new_filename = f"{uuid.uuid4()}_{date_str}.{extension}"
    return os.path.join('farm_image', new_filename)

# S3에서 파일 삭제하는 함수
def delete_s3_file(file_name):
    try:
        s3 = boto3.client('s3',
                          aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                          region_name=settings.AWS_REGION)
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        s3.delete_object(Bucket=bucket, Key=file_name)
    except Exception as e:
        logger.error(f"Error deleting file from S3: {e}")

def polygon_detection(center_lat,center_lon,coords):
    # UTM 좌표를 WGS84 좌표로 변환
    latlon_coords = transform_coords(coords)

    # WGS84 좌표를 픽셀 좌표로 변환
    pixel_coords = [geo_to_pixel(lat, lon, center_lat, center_lon) for lon, lat in latlon_coords]

    # 폴리곤으로 변환
    polygon = Polygon(pixel_coords)

    return polygon

def transform_coords(utm_coords, from_epsg=5186, to_epsg=4326):
    utm_coords = list(utm_coords.exterior.coords)
    transformer = Transformer.from_crs(from_epsg, to_epsg, always_xy=True)
    latlon_coords = [transformer.transform(x, y) for x, y in utm_coords]
    return latlon_coords

def geo_to_pixel(lat, lon, center_lat, center_lon, zoom=18, pixel_distance=0.229, tile_size=512):
    # 위도 및 경도 거리 차이 계산
    delta_lat = lat - center_lat
    delta_lon = lon - center_lon

    # 위도 및 경도 거리 (미터) 변환
    d_lat = delta_lat * 111320  # 위도 1도당 약 111.32 km
    d_lon = delta_lon * (111320 * math.cos(math.radians(center_lat)))  # 경도 1도당 거리

    # 거리 차이를 픽셀 차이로 변환
    delta_y = d_lat / pixel_distance
    delta_x = d_lon / pixel_distance

    # 중심 기준 픽셀 좌표 계산 (이미지 중심은 tile_size / 2)
    center_pixel = tile_size / 2
    pixel_x = center_pixel + delta_x
    pixel_y = center_pixel - delta_y

    return pixel_x, pixel_y

def function(center_lat, center_lon, coords):
    # UTM 좌표를 WGS84 좌표로 변환
    latlon_coords = transform_coords(coords)

    # WGS84 좌표를 픽셀 좌표로 변환
    pixel_coords = [geo_to_pixel(lat, lon, center_lat, center_lon) for lon, lat in latlon_coords]

    # 폴리곤으로 변환
    polygon = Polygon(pixel_coords)

    return polygon

def string_to_polygon(polygon_str):
    coordinates = polygon_str.replace('POLYGON ((', '').replace('))', '').replace(')', '').replace('(', '').split(', ')
    coordinates = [tuple(map(float, coord.split())) for coord in coordinates]
    return Polygon(coordinates)

def make_result_df(image):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    saved_model_path = os.path.join(project_root, 'openfield', 'best_pt.pt')
    loaded_model = YOLO(saved_model_path, task='detect')  # 에러 안나는곳 여기까지 확인함 
    predictions = loaded_model.predict(source=image, line_width=2)
    
    data_rows = []
    for i in range(len(predictions)):
        boxes = predictions[i].boxes  # 바운딩 박스 #필요
        num_elements = boxes.cls.size(0)  # 바운딩 박스 갯수 # 필요 

        for j in range(num_elements):
            x = boxes.xywh[j][0].item() # 바운딩 박스의 중심좌표 x  # 필요 
            y = boxes.xywh[j][1].item()  # 바운딩 박스의 중심좌표 y # 필요 
            width=boxes.xywh[j][2].item()
            height=boxes.xywh[j][3].item()  
            
            conf = boxes.data[j][4].item()  # 바운딩 박스의 확률 ( 정확도 )  # 준필요(기준으로 필터링 가능)
            class_id = boxes.data[j][5].item() # 클래스 (0: 건물 , 1: 태양광 , 2: 비닐하우스 )  # 필요

            data_rows.append({'x': x, 'y': y,'width':width,'height':height, 'conf': conf, 'class': class_id})

    df2 = pd.DataFrame(data_rows)
    return df2

def point_in_polygon(x, y, polygon):
    point = Point(x, y)
    return polygon.contains(point)

def polygon_function(center_lat, center_lon, coords):
    # UTM 좌표를 WGS84 좌표로 변환
    latlon_coords = transform_coords(coords)

    # WGS84 좌표를 픽셀 좌표로 변환
    pixel_coords = [geo_to_pixel(lat, lon, center_lat, center_lon) for lon, lat in latlon_coords]

    # 폴리곤으로 변환
    polygon = Polygon(pixel_coords)

    return polygon

def csv_exception(self, request, csv_file):
    if not csv_file:
        self.message_user(request, "CSV 파일을 선택해 주세요", level=messages.ERROR)
        return None  
    if not csv_file.name.endswith('.csv'):
        self.message_user(request, "CSV 파일이 아닙니다", level=messages.ERROR)
        return None  
    return csv_file  

def read_csv_file(csv_file):
    raw_data = csv_file.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding'] if result['encoding'] is not None else 'utf-8'
    return raw_data, encoding

def preprocess_dataframe(csv_file, raw_data, encoding):
    csv_file.seek(0)  # 파일 포인터를 처음으로 되돌림
    df = pd.read_csv(BytesIO(raw_data), encoding=encoding)
    df['geometry'] = df['geometry'].apply(string_to_polygon)
    df['pixel_polygon'] = df.apply(lambda row: polygon_function(row['위도'], row['경도'], row['geometry']), axis=1)
    return df

def decode_raw_data(raw_data, encoding):
    return raw_data.decode(encoding).splitlines()

def create_farm(row):
    from .models import Farm  # 지연 로딩
    farm_owner = row.get('소유구분')
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

def create_farm_status_log(farm, row):
    from .models import FarmStatusLog  # 지연 로딩
    farm_status = int(row.get('상태', 1))
    user_id = int(row.get('사용자', 1))
    FarmStatusLog.objects.create(
        farm=farm,
        farm_status=farm_status,
        user_id=user_id,
    )

def process_farm_images(self, request, farm, row):
    from .models import FarmImage # 지연 로딩
    try:
        image_content = get_satellite_image(farm.longitude, farm.latitude)
        image = Image.open(BytesIO(image_content))

        FarmImage.objects.create(
            farm=farm,
            farm_image=ContentFile(image_content, f"farm_image_{farm.farm_id}.jpg")
        )

        polygon = polygon_function(farm.latitude, farm.longitude, farm.farm_geometry)
        model_result_df = make_result_df(image)
        model_result_df['inside_polygon'] = None

        image = draw_detected_objects(image, model_result_df, polygon, farm)
        save_farm_polygon_image(image, farm)

    except UnidentifiedImageError:
        self.message_user(request, "이미지를 열 수 없습니다. 파일이 손상되었거나 지원되지 않는 형식일 수 있습니다.", level=messages.ERROR)
    except Exception as e:
        self.message_user(request, f"이미지 처리 중 오류 발생: {e}", level=messages.ERROR)

def draw_detected_objects(image, model_result_df, polygon, farm):
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

def draw_rectangle(image, df_row, font):
    top_left = (int(df_row['x'] - df_row['width'] / 2), int(df_row['y'] - df_row['height'] / 2))
    top_left_text = (int(df_row['x'] - df_row['width'] / 2), int(df_row['y'] - df_row['height'] / 2) - 6)
    bottom_right = (int(df_row['x'] + df_row['width'] / 2), int(df_row['y'] + df_row['height'] / 2))
    
    colors = {0: (0, 0, 255), 1: (255, 0, 0), 2: (0, 255, 0)}
    color = colors.get(df_row['class'], (0, 0, 0))
    cv2.rectangle(image, top_left, bottom_right, color, 3)
    cv2.putText(image, str(round(df_row['conf'], 2)), top_left_text, font, 0.5, color, 1, cv2.LINE_AA)

def update_farm_illegal_building_log(df_row, farm, cnt):
    from .models import FarmIllegalBuildingLog  # 지연 로딩
    if df_row['class'] == 0 and cnt == 0:
        FarmIllegalBuildingLog.objects.create(farm=farm, farm_illegal_building_status=1)
        cnt = 1
    return cnt

def save_farm_polygon_image(image, farm):
    from .models import FarmPolygonDetectionImage  # 지연 로딩
    output = BytesIO()
    image.save(output, format='JPEG')
    new_filename = f"{farm.farm_id}_{datetime.now().strftime('%Y%m%d')}.jpg"
    FarmPolygonDetectionImage.objects.create(
        farm=farm,
        farm_pd_image=ContentFile(output.getvalue(), new_filename)
    )
    output.close()
