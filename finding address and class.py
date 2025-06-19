import requests
import json

# 본인의 REST API 키를 입력하세요
KAKAO_API_KEY = "eaa0dfa461ea8729abbc659b6e987d76"

def search_place(query):
    """
    카카오 로컬 API를 사용하여 키워드로 장소를 검색하고,
    첫 번째 검색 결과의 상호명, 주소, 카테고리 그룹 코드를 반환합니다.
    """
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    
    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }
    
    params = {
        "query": query,
        "page": 1,
        "size": 1 # 가장 정확도 높은 1개의 결과만 받음
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
        
        data = response.json()
        
        # 검색 결과가 있는지 확인
        if not data.get('documents'):
            print(f"'{query}'에 대한 검색 결과가 없습니다.")
            return None
            
        # 첫 번째 검색 결과에서 정보 추출
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
        # API 키가 잘못되었거나 API 할당량을 초과했을 수 있습니다.
        try:
            error_data = response.json()
            print(f"카카오 서버 응답: {error_data}")
        except json.JSONDecodeError:
            print("오류 응답을 JSON으로 파싱할 수 없습니다.")
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        
    return None


# --- 코드 실행 예시 ---
if __name__ == "__main__":
    # 검색하고 싶은 상호명을 입력하세요.
    search_query = "서울시청" 
    # search_query = "서울시청"
    # search_query = "제주공항"
    
    result = search_place(search_query)

    # if result:
    #     print("\n반환된 데이터:", result) .