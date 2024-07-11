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
from django.http import HttpResponseRedirect
from PIL import Image, ImageDraw
from ultralytics import YOLO
from pyproj import Transformer
import math
from shapely.geometry import Polygon, Point
import pandas as pd
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
