import cv2
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from collections import Counter
from datetime import datetime
import uuid
import os


def generate_farm_image_filename(filename):
    extension = filename.split('.')[-1]
    date_str = datetime.now().strftime('%Y%m%d')
    new_filename = f"{uuid.uuid4()}_{date_str}.{extension}"
    return os.path.join('farm_image', new_filename)

def find_vector_set(diff_image, new_size):
    i = 0
    j = 0
    vector_set = np.zeros((int(new_size[0] * new_size[1] / 25), 25))
    while i < vector_set.shape[0]:
        while j < new_size[1]:
            k = 0
            while k < new_size[0]:
                block = diff_image[j:j + 5, k:k + 5]
                feature = block.ravel()
                vector_set[i, :] = feature
                k = k + 5
            j = j + 5
        i = i + 1

    mean_vec = np.mean(vector_set, axis=0)
    vector_set = vector_set - mean_vec
    return vector_set, mean_vec

def find_FVS(EVS, diff_image, mean_vec, new):
    i = 2
    feature_vector_set = []
    while i < new[1] - 2:
        j = 2
        while j < new[0] - 2:
            block = diff_image[i - 2:i + 3, j - 2:j + 3]
            feature = block.flatten()
            feature_vector_set.append(feature)
            j = j + 1
        i = i + 1

    FVS = np.dot(feature_vector_set, EVS)
    FVS = FVS - mean_vec
    return FVS

def clustering(FVS, components, new):
    kmeans = KMeans(components, verbose = 0)
    kmeans.fit(FVS)
    output = kmeans.predict(FVS)
    count  = Counter(output)
 
    least_index = min(count, key = count.get)
    change_map  = np.reshape(output,(new[1] - 4, new[0] - 4))
    return least_index, change_map


def perform_pca_and_clustering(image1_path, image2_path):
    # Read Images
    image1 = cv2.imread(image1_path)
    image2 = cv2.imread(image2_path)

    # Resize Images
    new_size = np.asarray(image1.shape) / 5 
    new_size = new_size.astype(int)*5
    image1 = cv2.resize(image1, (new_size[0], new_size[1])).astype(int)
    image2 = cv2.resize(image2, (new_size[0], new_size[1])).astype(int)
    
    # Difference Image  
    diff_image = np.abs(image1 - image2)  

    # Perform PCA
    pca = PCA()
    vector_set, mean_vec = find_vector_set(diff_image[:,:,1], new_size)
    pca.fit(vector_set)
    EVS = pca.components_

    # Build Feature Vector Space
    FVS = find_FVS(EVS, diff_image[:,:,1], mean_vec, new_size)

    # Clustering
    components = 2
    kmeans = KMeans(components, verbose=0)
    kmeans.fit(FVS)
    output = kmeans.predict(FVS)
    count = Counter(output)
    least_index = min(count, key=count.get)
    change_map = np.reshape(output, (new_size[1] - 4, new_size[0] - 4))

    change_map[change_map == least_index] = 255
    change_map[change_map != 255] = 0
    change_map = change_map.astype(np.uint8)

    # Generate filename and save the image
    farm_image_filename = generate_farm_image_filename("changemap.png")

    # Define the local path for saving the image
    local_image_path = os.path.join(farm_image_filename) 

    # Create directory if not exists
    os.makedirs(os.path.dirname(local_image_path), exist_ok=True)

    # Save the change_map image to the local path
    cv2.imwrite(local_image_path, change_map)

    return farm_image_filename

import cv2
import numpy as np
import re


def wkt_polygon_to_list(wkt_polygon):
    # 정규 표현식을 사용하여 숫자와 소수점을 추출하는 패턴
    pattern = r"[-+]?\d*\.\d+|\d+"

    # WKT 문자열에서 좌표 부분만 추출
    coords_str = re.findall(pattern, wkt_polygon)

    # 좌표를 실수형으로 변환하여 리스트로 저장
    coords = []
    for i in range(0, len(coords_str), 2):
        x = float(coords_str[i])
        y = float(coords_str[i+1])
        coords.append([x, y])

    # 마지막 점을 첫 번째 점과 동일하게 추가하여 폴리곤을 닫음
    coords.append(coords[0])
    print(f"coords:{coords}")
    return coords

def coords_to_string(coords): # coords 리스트를 문자열로 변환하는 함수
    return ', '.join(f"{x} {y}" for x, y in coords)

def parse_coords_string(coords_str):  # 좌표 문자열을 파싱하여 실수형 좌표 쌍의 리스트를 반환합니다.
    coords_pairs = coords_str.split(', ')
    coordinates = [tuple(map(float, pair.split())) for pair in coords_pairs]
    return coordinates

 # 변화 비율 계산 함수
def calculate_change_ratio(change_map_path, polygon_coords):
    # 변화 맵을 불러옵니다 (grayscale 이미지로 가정)
    change_map = cv2.imread(change_map_path, cv2.IMREAD_GRAYSCALE)

    # 폴리곤 좌표를 정수형으로 변환합니다
    polygon_coords = np.array(polygon_coords, dtype=np.int32)

    # 변화 맵과 같은 크기의 빈 이미지 생성
    polygon_mask = np.zeros_like(change_map, dtype=np.uint8)

    # 폴리곤 내부를 흰색(255)으로 채웁니다
    cv2.fillPoly(polygon_mask, [polygon_coords], 255)

    # 변화 맵에 폴리곤 마스크를 적용하여 해당 영역의 변화를 추출합니다
    polygon_change = cv2.bitwise_and(change_map, polygon_mask)

    # 폴리곤 내부의 흰색 픽셀 수 계산
    num_white_pixels_polygon = np.count_nonzero(polygon_change == 255)

    # 폴리곤 영역 전체 픽셀 수 계산
    total_pixels_polygon = np.count_nonzero(polygon_mask == 255)

    # 변화 비율 계산
    if total_pixels_polygon > 0:
        change_ratio_polygon = num_white_pixels_polygon / total_pixels_polygon
    else:
        change_ratio_polygon = 0.0

    return change_ratio_polygon
