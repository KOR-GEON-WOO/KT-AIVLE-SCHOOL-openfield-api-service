from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import numpy as np
import cv2
from .models import *
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from collections import Counter
import tempfile
from .utils import string_to_polygon,function

def save_open_map_image(image_bytes, filename):  #바이트 데이터를 이미지 파일로 저장하여 경로를 반환하는 함수
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_file.write(image_bytes)
    temp_file.close()
    return temp_file.name

def save_image_temp(image_field):  # 이미지 필드를 임시 파일로 저장하여 경로를 반환하는 함수
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_file.write(image_field.read())
    temp_file.close()
    return temp_file.name

def find_vector_set(diff_image, new_size):             # 변화탐지 
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
 
def find_FVS(EVS, diff_image, mean_vec, new):           # 변화탐지 
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

def clustering(FVS, components, new):               # 변화탐지 
    kmeans = KMeans(components, verbose = 0)
    kmeans.fit(FVS)
    output = kmeans.predict(FVS)
    count  = Counter(output)
 
    least_index = min(count, key = count.get)
    change_map  = np.reshape(output,(new[1] - 4, new[0] - 4))
    return least_index, change_map


def perform_pca_and_clustering(image1_path, image2_path):          # 변화탐지 
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
    diff_image=diff_image[:,:,1]
    vector_set, mean_vec = find_vector_set(diff_image, new_size)
    pca.fit(vector_set)
    EVS = pca.components_

    # Build Feature Vector Space
    FVS = find_FVS(EVS, diff_image, mean_vec, new_size)

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
    
    image = Image.fromarray(change_map)
    
    return image

def calculate_change_ratio(image, polygon_coords):          # 변화탐지 

    change_map = np.array(image)

    polygon_coords = np.array(polygon_coords, dtype=np.int32)

    polygon_mask = np.zeros_like(change_map, dtype=np.uint8)

    cv2.fillPoly(polygon_mask, [polygon_coords], 255)

    polygon_change = cv2.bitwise_and(change_map, polygon_mask)

    num_white_pixels_polygon = np.count_nonzero(polygon_change == 255)
    total_pixels_polygon = np.count_nonzero(polygon_mask == 255)

    if total_pixels_polygon > 0:
        change_ratio_polygon = num_white_pixels_polygon / total_pixels_polygon
    else:
        change_ratio_polygon = 0.0

    return change_ratio_polygon

def makeChangeRate(farm_id):                         # 변화탐지 
    from .models import Farm ,FarmChangeDetection,FarmChangeDetectionLog
    query = FarmChangeDetection.objects.filter(farm_id=farm_id).order_by('farm_change_detection_created')
    farm_geometry = Farm.objects.filter(farm_id=farm_id).values_list('farm_geometry',flat=True).first() 
    center_lat = float(Farm.objects.filter(farm_id=farm_id).values('latitude').first()['latitude'])
    center_lon = float(Farm.objects.filter(farm_id=farm_id).values('longitude').first()['longitude'])

    pixel_polygon = function(center_lat, center_lon, string_to_polygon(farm_geometry))
    pixel_polygon = list(pixel_polygon.exterior.coords)
    
    image_path1 = save_image_temp(query[2].farm_change_detection_image)
    image_path2 = save_image_temp(query[1].farm_change_detection_image)
    image_path3 = save_image_temp(query[0].farm_change_detection_image)

    open_map_image1 = perform_pca_and_clustering(image_path1, image_path2)
    open_map_image2 = perform_pca_and_clustering(image_path2, image_path3) 

    change_ratio1 = calculate_change_ratio(open_map_image1, pixel_polygon)  
    change_ratio2 = calculate_change_ratio(open_map_image2, pixel_polygon)
    result = change_ratio1 * 100 if change_ratio1 > change_ratio2 else change_ratio2 * 100

    output1=BytesIO()
    output2=BytesIO()
    open_map_image1.save(output1,format='JPEG')
    open_map_image2.save(output2,format='JPEG')

    FarmChangeDetectionLog.objects.create(
        farm_id=farm_id,
        farm_change_detection_result_image1=ContentFile(output1.getvalue(), f"farm_image_1_{farm_id}.png"),
        farm_change_detection_result_image2=ContentFile(output2.getvalue(), f"farm_image_2_{farm_id}.png"),
        change_rating1=change_ratio1,
        change_rating2=change_ratio2,
        change_rating_result=result,
    )