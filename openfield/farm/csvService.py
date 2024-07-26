from django.contrib import messages
import pandas as pd
import chardet
from io import BytesIO
from .utils import string_to_polygon,function

def csv_exception(self, request, csv_file):        # csv 예외처리 
    if not csv_file:
        self.message_user(request, "CSV 파일을 선택해 주세요", level=messages.ERROR)
        return None  
    if not csv_file.name.endswith('.csv'):
        self.message_user(request, "CSV 파일이 아닙니다", level=messages.ERROR)
        return None  
    return csv_file  

def read_csv_file(csv_file):             # csv 파일 읽기 
    raw_data = csv_file.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding'] if result['encoding'] is not None else 'utf-8'
    return raw_data, encoding

def preprocess_dataframe(csv_file, raw_data, encoding):  # df 초기화 읽어 오기 
    csv_file.seek(0)  # 파일 포인터를 처음으로 되돌림
    df = pd.read_csv(BytesIO(raw_data), encoding=encoding)
    df['geometry'] = df['geometry'].apply(string_to_polygon)
    df['pixel_polygon'] = df.apply(lambda row: function(row['위도'], row['경도'], row['geometry']), axis=1)
    return df

def decode_raw_data(raw_data, encoding):             # df 읽기 
    return raw_data.decode(encoding).splitlines()