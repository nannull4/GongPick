import requests
import json
import os
from dotenv import load_dotenv

# =================================================== #
# 아래 두 줄을 코드 상단에 추가하여 출력 인코딩을 UTF-8로 강제합니다.
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# =================================================== #

# .env 파일에서 환경 변수를 불러옴
load_dotenv()

# os.getenv()를 사용하여 환경 변수에서 API 키를 가져옴
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

# (이하 나머지 코드는 모두 동일)
# ... (기존 코드를 그대로 두시면 됩니다) ...

def search_place(query):
    # ... (함수 내용 동일) ...
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    
    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }
    
    params = {
        "query": query,
        "page": 1,
        "size": 1 
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('documents'):
            print(f"'{query}'에 대한 검색 결과가 없습니다.")
            return None
            
        first_result = data['documents'][0]
        place_name = first_result.get('place_name')
        address = first_result.get('road_address_name') or first_result.get('address_name')
        category_code = first_result.get('category_group_code')
        category_name = first_result.get('category_name')

        print("--- 검색 결과 ---")
        print(f"상호명: {place_name}")
        print(f"주소: {address}")
        print(f"업종 코드: {category_code}")
        print(f"카테고리: {category_name}")
        
        return {
            'place_name': place_name,
            'address': address,
            'category_code': category_code
        }

    except requests.exceptions.HTTPError as err:
        print(f"API 요청 중 HTTP 오류가 발생했습니다: {err}")
        try:
            error_data = response.json()
            print(f"카카오 서버 응답: {error_data}")
        except json.JSONDecodeError:
            print("오류 응답을 JSON으로 파싱할 수 없습니다.")
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        
    return None

if __name__ == "__main__":
    search_query = "서울시청" 
    result = search_place(search_query)