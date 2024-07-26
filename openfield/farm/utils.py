import boto3
import logging
import os
from django.conf import settings
from ultralytics import YOLO
from pyproj import Transformer
import math
from shapely.geometry import Polygon, Point
import pandas as pd
from .models import *
import re
from shapely.geometry import Polygon

logger = logging.getLogger(__name__)

def delete_s3_file(file_name):                          # S3에서 파일 삭제하는 함수
    try:
        s3 = boto3.client('s3',
                          aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                          region_name=settings.AWS_REGION)
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        s3.delete_object(Bucket=bucket, Key=file_name)
    except Exception as e:
        logger.error(f"Error deleting file from S3: {e}")

def transform_coords(utm_coords, from_epsg=5186, to_epsg=4326):    # GIS 좌표를 변환 
    utm_coords = list(utm_coords.exterior.coords)
    transformer = Transformer.from_crs(from_epsg, to_epsg, always_xy=True)
    latlon_coords = [transformer.transform(x, y) for x, y in utm_coords]
    return latlon_coords

def geo_to_pixel(lat, lon, center_lat, center_lon, zoom=18, pixel_distance=0.229, tile_size=512): # 지리적 위도,경도를 픽셀 이미지위로 변환
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

def function(center_lat, center_lon, coords):       # UTM 좌표를 폴리곤으로 변환
    # UTM 좌표를 WGS84 좌표로 변환
    latlon_coords = transform_coords(coords)

    # WGS84 좌표를 픽셀 좌표로 변환
    pixel_coords = [geo_to_pixel(lat, lon, center_lat, center_lon) for lon, lat in latlon_coords]

    # 폴리곤으로 변환
    polygon = Polygon(pixel_coords)

    return polygon

def string_to_polygon(polygon_str):   # string 타입을 polygon 변환 
    coordinates = polygon_str.replace('POLYGON ((', '').replace('))', '').replace(')', '').replace('(', '').split(', ')
    coordinates = [tuple(map(float, coord.split())) for coord in coordinates]
    return Polygon(coordinates)

def make_result_df(image):           # 객체 탐지 수행 후 df 에 저장 
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    saved_model_path = os.path.join(project_root, 'openfield', 'best.pt')
    loaded_model = YOLO(saved_model_path, task='detect')   
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

def wkt_polygon_to_list(wkt_polygon):           # 폴리곤 좌표 변환 

    pattern = r"[-+]?\d*\.\d+|\d+"
    coords_str = re.findall(pattern, wkt_polygon)

    coords = []
    for i in range(0, len(coords_str), 2):
        x = float(coords_str[i])
        y = float(coords_str[i+1])
        coords.append([x, y])

    coords.append(coords[0])
    print(f"coords:{coords}")
    return coords

def coords_to_string(coords):                     # 좌표 변환 
    return ', '.join(f"{x} {y}" for x, y in coords)

def parse_coords_string(coords_str):               # 좌표 변환
    coords_pairs = coords_str.split(', ')
    coordinates = [tuple(map(float, pair.split())) for pair in coords_pairs]
    return coordinates