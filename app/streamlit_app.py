import streamlit as st
import os
import json
from openai import AzureOpenAI
import pandas as pd
import joblib
import numpy as np
import folium
from streamlit_folium import st_folium
from PIL import Image # 로고 이미지를 위해 추가

# --- 1. Azure OpenAI 설정 (실제 환경에 맞게 조정하세요) ---
# 환경 변수에서 API 키, 엔드포인트 등을 불러오는 것을 권장합니다.
# 예시:
# azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
# azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
# azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
# your_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")

# 현재 예시에서는 코드로 직접 값을 할당합니다.
azure_openai_api_key = "" # 실제 키로 변경하세요
azure_openai_endpoint = "" # 실제 엔드포인트로 변경하세요
azure_openai_api_version = "2024-02-15-preview"
your_deployment_name = "gpt-4o-mini" # 실제 배포 이름으로 변경하세요

# AzureOpenAI 클라이언트 초기화
try:
    client = AzureOpenAI(
        api_key=azure_openai_api_key,
        azure_endpoint=azure_openai_endpoint,
        api_version=azure_openai_api_version
    )
    st.success("Azure OpenAI 클라이언트가 성공적으로 초기화되었습니다.")
except Exception as e:
    st.error(f"Azure OpenAI 클라이언트 초기화 오류: {e}")
    st.stop() # 클라이언트 초기화 실패 시 앱 실행 중단

# --- 2. 시스템 프롬프트 정의 ---
system_prompt_content = """
You are an AI assistant designed to extract dining preferences from user queries and format them into a structured JSON object.
Your primary goal is to **always output a JSON object** following the specified schema.
You must not provide any additional conversational text, explanations, or deviations from this JSON format.

**JSON Output Format:**

```json
{
    "인원": [Integer],
    "계절": [String, e.g., "봄", "여름", "가을", "겨울"],
    "점저": [String, e.g., "점심", "저녁"],
    "1인당비용": [Integer],
    "업종 중분류": [String, e.g., "한식", "양식", "중식", "일식", "카페/디저트", "술집", "치킨", "분식", "패스트푸드" 등 구체적인 음식/업종 카테고리],
    "구": [String, e.g., "강남구", "마포구", "중구", "종로구", "서초구", "영등포구" 등 대한민국 서울특별시 및 주요 도시의 실제 '구' 이름. 만약 '구' 정보가 명확하지 않거나 대한민국이 아닌 지역이 언급되면, 사용자에게 직접 묻거나 가장 합리적인 서울/경기권 '구'로 가정합니다.]
}
```

**Instructions for Populating the JSON Fields:**

* **인원 (Participants):**
    * Extract the number of people directly mentioned.
    * If not explicitly stated, infer based on common phrases (e.g., "혼자" -> 1, "둘이서" -> 2, "팀원들" -> 문맥상 파악 가능한 인원 또는 합리적인 기본값).
    * If no clear number is inferable, default to `1`.
* **계절 (Season):**
    * Always determine the current season based on the current date. (현재는 여름으로 설정).
* **점저 (Meal Time):**
    * Determine if the user is referring to "점심" (lunch) or "저녁" (dinner) based on keywords like "점심", "저녁", "회식", "퇴근 후", "아침" (이 경우 점심 또는 저녁으로 변환).
    * If ambiguous, default to "저녁".
* **1인당비용 (Cost per Person):**
    * Calculate this by dividing the total budget by the number of people.
    * If a total budget is given without the number of people, use the inferred number of people.
    * If neither total budget nor explicit cost per person is given, infer a reasonable cost per person based on the `업종 중분류` (e.g., 치킨/분식은 저렴하게, 양식/일식은 높게).
* **업종 중분류 (Cuisine/Category):**
    * Identify the most specific type of cuisine or establishment mentioned (e.g., "한식", "양식", "중식", "일식", "카페/디저트", "술집", "치킨", "피자", "분식", "패스트푸드").
    * Be flexible with synonyms and general terms.
    * If no specific type is mentioned, try to infer from the context (e.g., "밥 먹자" -> "한식"). If still unclear, default to "한식".
* **구 (District):**
    * Extract the specific '구' name (e.g., "강남구", "마포구", "중구").
    * **CRITICAL:** If the user mentions a location outside of South Korea (e.g., "미국", "중국", "뉴욕", "신주쿠구") or a clearly non-existent district, still extract what they said into the `구` field. **DO NOT** output a "service not supported" message from the LLM. The downstream application will handle this validation.
    * If no district is mentioned, assume a reasonable default based on common activity (e.g., "중구" 또는 "강남구" 등 서울의 중심지).

**Example Scenarios:**

* **Scenario 1 (Normal):**
    * **User Input:** "나는 마포구에서 회사를 다니는 직장인이야 오늘 저녁에 팀원 8명과 중식집에서 총 30만원 이내로 회식을 하려고 해"
    * **Expected Output:**
        ```json
        {
            "인원": 8,
            "계절": "여름",
            "점저": "저녁",
            "1인당비용": 37500,
            "업종 중분류": "중식",
            "구": "마포구"
        }
        ```
* **Scenario 2 (Ambiguous/Missing Info):**
    * **User Input:** "오늘 점심 뭐 먹지?"
    * **Expected Output (assuming 1인당비용은 문맥상 합리적으로 추론):**
        ```json
        {
            "인원": 1,
            "계절": "여름",
            "점저": "점심",
            "1인당비용": 10000,
            "업종 중분류": "한식",
            "구": "중구"
        }
        ```
* **Scenario 3 (Foreign District - LLM still extracts it):**
    * **User Input:** "도쿄 신주쿠구에서 맛있는 라멘집 알려줘"
    * **Expected Output:**
        ```json
        {
            "인원": 1,
            "계절": "여름",
            "점저": "저녁",
            "1인당비용": 15000,
            "업종 중분류": "일식",
            "구": "신주쿠구"
        }
        ```
"""

# --- 3. 서비스 지원 지역 리스트 ---
# 실제 데이터베이스나 설정 파일에서 불러오는 것을 권장합니다.
valid_korean_districts = [
    "강남구", "마포구", "중구", "종로구", "서초구", "영등포구", "관악구", "동작구", "성동구", 
    "송파구", "강서구", "노원구", "동대문구", "은평구", "서대문구", "성북구", "용산구", 
    "양천구", "도봉구", "구로구", "금천구", "중랑구", "강북구", "광진구"
]

# --- 4. ML 모델 로드 ---
# 'ML_model.pkl' 파일이 Streamlit 앱이 실행되는 디렉토리에 있다고 가정합니다.
# 실제 모델 경로와 파일명을 사용하세요.
try:
    pipeline = joblib.load('ML_model.pkl')
    st.success("ML 모델 (ML_model.pkl)이 성공적으로 로드되었습니다.")
except FileNotFoundError:
    st.error("ML 모델 파일 (ML_model.pkl)을 찾을 수 없습니다. 파일 경로를 확인해주세요.")
    st.stop()
except Exception as e:
    st.error(f"ML 모델 로드 중 오류 발생: {e}")
    st.stop()

# --- 5. 학습 데이터프레임 시뮬레이션 또는 로드 ---
# ML 모델이 'pipeline.classes_'를 가지고 있고, 'df' 데이터프레임에 '사용장소'와 '업종 중분류', 그리고 지도 표시를 위한 위도/경도가 있다고 가정합니다.
# 실제 환경에서는 이 'df'를 CSV 파일 등에서 로드해야 합니다.
# 예를 들어: df = pd.read_csv('your_data.csv')
if 'df' not in st.session_state:
    # 예시 데이터 생성 (실제 데이터로 대체해야 합니다)
    st.session_state.df = pd.DataFrame({
        "인원": [1, 2, 4, 8, 2, 1, 3, 5, 2, 6, 1],
        "계절": ["여름", "여름", "여름", "여름", "가을", "겨울", "여름", "봄", "여름", "가을", "겨울"],
        "점저": ["점심", "저녁", "저녁", "저녁", "저녁", "점심", "점심", "점심", "저녁", "저녁", "점심"], # '점저'로 통일
        "1인당비용": [15000, 50000, 25000, 37500, 45000, 10000, 12000, 18000, 30000, 22000, 8000],
        "업종 중분류": ["한식", "양식", "중식", "중식", "일식", "한식", "치킨", "한식", "양식", "한식", "분식"],
        "구": ["중구", "중구", "마포구", "마포구", "강남구", "종로구", "마포구", "영등포구", "강남구", "마포구", "중구"],
        "사용장소": [
            "명동칼국수", "이태원 비스트로", "연남동 중식당", "공덕 회관", 
            "강남 스시집", "종로 설렁탕", "홍대 치킨집", "여의도 부대찌개",
            "청담 이탈리안", "합정 삼겹살하우스", "시청 김밥천국"
        ],
        "lat": [37.5630, 37.5348, 37.5580, 37.5450, 37.5170, 37.5700, 37.5560, 37.5210, 37.5250, 37.5502, 37.5650], 
        "lon": [126.9800, 126.9920, 126.9360, 126.9480, 127.0200, 126.9890, 126.9230, 126.9380, 127.0450, 126.9149, 126.9770]
    })


# --- 페이지 설정 (반드시 최상단에서 호출) ---
st.set_page_config(page_title="공무원 맛집 추천 시스템", layout="wide")

# 초기 세션 상태 설정
if "chat_input" not in st.session_state:
    st.session_state.chat_input = ""
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "selected_similar" not in st.session_state:
    st.session_state.selected_similar = None
if "show_response" not in st.session_state:
    st.session_state.show_response = False
if "show_input" not in st.session_state:
    st.session_state.show_input = True
if "query" not in st.session_state:
    st.session_state.query = {}
if "llm_parsed_data" not in st.session_state: # LLM 파싱 데이터 저장
    st.session_state.llm_parsed_data = {}
if "predicted_place_info" not in st.session_state: # 예측된 장소 정보 저장 (lat, lon 포함)
    st.session_state.predicted_place_info = {}
if "similar_places_info" not in st.session_state: # 비슷한 장소 정보 저장
    st.session_state.similar_places_info = []

# === 사이드바 ===
with st.sidebar:
    # 'logo' 폴더와 'gongpicklogo.png' 파일이 스크립트와 같은 위치에 있다고 가정
    try:
        logo = Image.open("./logo/gongpicklogo.png")
        st.image(logo, use_column_width=True)
    except FileNotFoundError:
        st.warning("로고 파일을 찾을 수 없습니다. ./logo/gongpicklogo.png 경로를 확인하세요.")
        st.markdown("<h1 style='color: rgba(128, 144, 182, 1); font-weight: bold;'>Gongpick AI</h1>", unsafe_allow_html=True)
    
    st.markdown("<p style='color: rgba(128, 144, 182, 1); font-weight: bold;'>공무원들의 믿을만한 Pick!</p>", unsafe_allow_html=True)
    st.markdown("#### 오늘의 업무도 맛있게!")
    menu = st.radio("📋 메뉴", ["홈", "메뉴결정", "지도 보기", "이용 가이드"], index=0)

# === 홈 (챗봇) ===
if menu == "홈":
    st.markdown("<div id='top'></div>", unsafe_allow_html=True)

    if not st.session_state.show_response:
        st.markdown("""
            <div style='text-align: center; margin-top: 30px;'>
                <img src='https://img.icons8.com/fluency/96/000000/chat.png' width='72'/>
                <h1 style='font-weight: bold; font-size: 50px; margin-bottom: 0;'>Gong bot</h1>
                <p style='color: gray; font-size: 20px;'>🚀 배는 고픈데 결정은 못하겠다면? Gong bot 부르세요!</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 👇 아래 질문을 선택하거나 직접 입력해보세요!")

        example_questions = [
            "마포구에서 점심 먹을 건데 추천해줘 인당 12000원",
            "8명이 저녁에 회식할 건데 중식집으로 부탁해",
            "중구에서 여자친구랑 저녁 먹을만한 양식당 알려줘"
        ]
        cols = st.columns(3)
        for i, col in enumerate(cols):
            if col.button(f"💬 {example_questions[i]}", key=f"ex_{i}"):
                st.session_state.chat_input = example_questions[i]

        with st.form("chat_form"):
            user_query = st.text_input(
                "💬 쫄면이냐, 제육이냐… 오늘도 메뉴 고민 출근 완료 🤯",
                value=st.session_state.chat_input,
                key="chat_input_box"
            )
            col1, col2 = st.columns([1, 1])
            with col1:
                submitted = st.form_submit_button("질문하기")

            if submitted and user_query:
                st.session_state.last_query = user_query
                st.session_state.chat_input = user_query
                st.session_state.selected_similar = None # 새로운 쿼리 시 선택 초기화
                st.session_state.show_response = True
                st.rerun()

    else: # st.session_state.show_response가 True일 때 (질문 제출 후)
        st.markdown("---")
        if st.button("🔄 다시 질문하기"):
            st.session_state.show_response = False
            st.rerun()

        st.markdown("### 💬 답변")
        st.markdown(f"**'{st.session_state.last_query}'에 대한 추천 결과입니다.**")

        # --- LLM 및 ML 모델 로직 통합 ---
        with st.spinner("LLM으로 정보 추출 및 ML 모델로 추천 맛집 찾는 중..."):
            try:
                # LLM Chat Completion 요청
                response = client.chat.completions.create(
                    model=your_deployment_name,
                    messages=[
                        {
                            "role": "system",
                            "content": [{"type": "text", "text": system_prompt_content}]
                        },
                        {"role": "user", "content": st.session_state.last_query} # 저장된 마지막 쿼리 사용
                    ],
                    max_tokens=200,
                    response_format={"type": "json_object"}
                )

                llm_output_json_str = response.choices[0].message.content
                # st.subheader("LLM 원시 JSON 출력:") # 디버깅용
                # st.code(llm_output_json_str, language="json") # 디버깅용

                # JSON 파싱
                model_input_data = json.loads(llm_output_json_str)
                st.session_state.llm_parsed_data = model_input_data # 세션 상태에 저장
                # st.subheader("파싱된 데이터:") # 디버깅용
                # st.json(model_input_data) # 디버깅용

                # 서비스 미지원 지역 검사
                extracted_gu = model_input_data.get("구")

                if extracted_gu and extracted_gu not in valid_korean_districts:
                    st.error(f"🚨 서비스 미지원 지역입니다: **'{extracted_gu}'**.\n\n"
                             "대한민국 서울특별시 내의 '구' 단위 지역만 지원됩니다. 다시 질문해주세요.")
                    st.session_state.predicted_place_info = {} # 예측 정보 초기화
                    st.session_state.similar_places_info = [] # 비슷한 장소 정보 초기화
                else:
                    st.success(f"✅ '{extracted_gu}'는 지원되는 지역입니다. ML 모델 예측을 시작합니다.")
                    
                    # ML 모델 입력 데이터 준비 및 예측
                    # ML 모델이 기대하는 컬럼 순서 (df와 동일해야 함)
                    feature_columns = ["인원", "계절", "점저", "1인당비용", "업종 중분류", "구"]
                    
                    # 모든 필수 필드가 LLM 출력에 있는지 확인
                    if not all(field in model_input_data for field in feature_columns):
                        st.error("LLM 출력에 ML 모델 예측에 필요한 필수 필드가 누락되었습니다. 다시 질문해주세요.")
                        st.session_state.predicted_place_info = {}
                        st.session_state.similar_places_info = []
                    else:
                        # 숫자형 필드 타입 변환 (LLM이 문자열로 줄 수 있으므로)
                        try:
                            model_input_data["인원"] = int(model_input_data["인원"])
                            model_input_data["1인당비용"] = int(model_input_data["1인당비용"])
                        except ValueError:
                            st.error("LLM이 반환한 '인원' 또는 '1인당비용' 값이 유효한 숫자가 아닙니다. 다시 질문해주세요.")
                            st.session_state.predicted_place_info = {}
                            st.session_state.similar_places_info = []
                            st.stop() # 여기에서 return 대신 st.stop() 사용

                        # ML 모델에 전달할 DataFrame 생성 (명시적인 컬럼 순서 지정)
                        example = pd.DataFrame([model_input_data], columns=feature_columns)
                        
                        try:
                            predicted_probs = pipeline.predict_proba(example)
                            predicted_class_index = predicted_probs.argmax()
                            predicted_place_name = pipeline.classes_[predicted_class_index]
                            confidence = predicted_probs[0][predicted_class_index]

                            # 예측된 장소 정보 (위도, 경도 포함) 가져오기
                            df = st.session_state.df
                            predicted_place_row = df[df['사용장소'] == predicted_place_name]
                            
                            if not predicted_place_row.empty: # 예측된 장소가 df에 있는지 확인
                                predicted_place_row = predicted_place_row.iloc[0]
                                st.session_state.predicted_place_info = {
                                    "name": predicted_place_row['사용장소'],
                                    "address": f"서울 {predicted_place_row['구']} (예시 주소)", # 실제 주소는 데이터에 따라 다름
                                    "lat": predicted_place_row['lat'],
                                    "lon": predicted_place_row['lon'],
                                    "people_rec": "최대 10명", # 실제 모델에 따라 동적으로 변경
                                    "cost_per_person": predicted_place_row['1인당비용'],
                                    "category": predicted_place_row['업종 중분류']
                                }

                                st.markdown(f"#### 🍽️ 추천 맛집: {st.session_state.predicted_place_info['name']}")
                                st.markdown(f"""
                                    - 📍 주소: {st.session_state.predicted_place_info['address']}
                                    - 👥 인원 추천: {st.session_state.predicted_place_info['people_rec']}
                                    - 💰 인당 예산: {st.session_state.predicted_place_info['cost_per_person']}원 
                                    - ⭐ 업종: {st.session_state.predicted_place_info['category']}
                                """)
                                st.write(f"_(신뢰도: {confidence:.2%})_")

                                # 지도 표시 (예측된 맛집)
                                m = folium.Map(location=[st.session_state.predicted_place_info['lat'], st.session_state.predicted_place_info['lon']], zoom_start=17)
                                folium.Marker(
                                    location=[st.session_state.predicted_place_info['lat'], st.session_state.predicted_place_info['lon']],
                                    tooltip=st.session_state.predicted_place_info['name'],
                                    popup=st.session_state.predicted_place_info['address'],
                                    icon=folium.Icon(color="red", icon="cutlery", prefix="fa")
                                ).add_to(m)
                                st_folium(m, width=1000, height=600, key="predicted_map")

                                st.markdown("### 🔍 비슷한 장소 추천")
                                # 동일 업종 중분류 및 구 내 비슷한 장소 3개 추천
                                similar_places_df = df[(df['업종 중분류'] == st.session_state.predicted_place_info['category']) & 
                                                       (df['구'] == model_input_data['구']) &
                                                       (df['사용장소'] != st.session_state.predicted_place_info['name'])]
                                
                                # 랜덤으로 3개 선택 (실제로는 ML 모델의 유사도 점수 등에 따라 선정)
                                # 데이터가 충분하지 않을 경우를 대비하여 min(3, len(similar_places_df))
                                num_similars = min(3, len(similar_places_df))
                                if num_similars > 0:
                                    st.session_state.similar_places_info = similar_places_df.sample(n=num_similars).to_dict(orient='records')
                                else:
                                    st.session_state.similar_places_info = []

                                sim_cols = st.columns(3)
                                if st.session_state.similar_places_info:
                                    for i, sim_place in enumerate(st.session_state.similar_places_info):
                                        selected = (st.session_state.selected_similar == i)
                                        background = "#ffe6e6" if selected else "#f9f9f9"
                                        border = "2px solid #ff4d4d" if selected else "1px solid #ddd"
                                        with sim_cols[i]:
                                            if st.button(f"✨ {sim_place['사용장소']}", key=f"sim_{i}"):
                                                st.session_state.selected_similar = i
                                                st.rerun()
                                            st.markdown(f"""
                                            <div style='border:{border}; border-radius:10px; padding:15px; background-color:{background};'>
                                                <p style='margin:0;'>📍 {sim_place['구']} (예시 주소)</p>
                                                <p style='margin:0;'>💰 {sim_place['1인당비용']}원</p>
                                                <p style='margin:0;'>⭐ {sim_place['업종 중분류']}</p>
                                            </div>
                                            """, unsafe_allow_html=True)
                                else:
                                    st.info("비슷한 추천 장소를 찾을 수 없습니다.")

                                if st.session_state.selected_similar is not None and st.session_state.similar_places_info:
                                    st.markdown("""
                                    <script>
                                    const similarMap = document.getElementById('similar_map');
                                    if (similarMap) {
                                        similarMap.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                    }
                                    </script>
                                    """, unsafe_allow_html=True)

                                    sel = st.session_state.similar_places_info[st.session_state.selected_similar]
                                    st.markdown("### 📍 선택한 장소 위치")
                                    st.markdown("<div id='similar_map'></div>", unsafe_allow_html=True)
                                    m2 = folium.Map(location=[sel["lat"], sel["lon"]], zoom_start=17)
                                    folium.Marker(
                                        location=[sel["lat"], sel["lon"]],
                                        popup=sel["사용장소"],
                                        tooltip=f"{sel['사용장소']} ({sel['구']})",
                                        icon=folium.Icon(color="orange", icon="star", prefix="fa")
                                    ).add_to(m2)
                                    st_folium(m2, width=800, height=500, key="similar_map_display")
                            else: # 예측된 장소가 df에 없는 경우
                                st.warning(f"예측된 장소 '{predicted_place_name}'에 대한 상세 정보를 찾을 수 없습니다. (ML 모델의 예측 결과가 학습 데이터에 없을 수 있음)")

                        except Exception as ml_e:
                            st.error(f"ML 모델 예측 중 오류 발생: {ml_e}")
                            st.info("💡 팁: ML 모델 (ML_model.pkl)이 'pipeline.classes_' 속성을 가지는지 또는 예측 후 레이블을 매핑하는 추가 로직이 필요한지, 그리고 입력 데이터의 컬럼 순서와 타입이 모델 학습 시와 일치하는지 확인해보세요.")

            except json.JSONDecodeError:
                st.error("❌ LLM 출력 JSON 파싱 오류. 모델이 올바른 JSON 형식을 반환하는지 확인하세요. 다시 질문해주세요.")
            except Exception as e:
                st.error(f"⚠️ API 호출 또는 처리 중 오류 발생: {e}. 다시 질문해주세요.")

        st.markdown("""
        <div style="text-align: right; margin-top: 20px;">
            <a href="#top" style="font-weight: bold; text-decoration: none; font-size: 18px;">🔝 맨 위로</a>
        </div>
        """, unsafe_allow_html=True)

# === 메뉴결정 (기존 코드 유지) ===
elif menu == "메뉴결정":
    st.title("🍱 공무원 현지 맛집 추천")
    if st.session_state.show_input:
        with st.form("input_form"):
            st.subheader("🔍 지금 가장 중요한 회의는 메뉴 결정입니다 👔🍽️")
            category = st.selectbox("🍽 업종 분류", ["한식", "중식", "일식", "양식", "카페", "기타"])
            season = st.radio("🍂 계절", ["봄", "여름", "가을", "겨울"], horizontal=True)
            time_slot = st.radio("⏰ 식사 시간", ["점심", "저녁"], horizontal=True)
            district = st.text_input("📍 구 (ex: 강남구, 중구)")
            cost = st.text_input("💰 1인당 비용 (ex: 12000)")
            people_count = st.number_input("👥 인원 수", min_value=1, value=1, step=1)
            submitted = st.form_submit_button("🔎 맛집 추천 검색")
            if submitted:
                st.session_state.show_input = False
                st.session_state.query = {
                    "인원": people_count,
                    "계절": season,
                    "점저": time_slot, # '시간대'를 '점저'로 통일
                    "1인당비용": int(cost) if cost.isdigit() else 0, # 문자열을 숫자로 변환
                    "업종 중분류": category,
                    "구": district
                }
                # '메뉴결정' 탭에서도 ML 모델을 사용하려면 아래 로직을 추가
                # 현재는 LLM을 통한 통합 흐름이 아니므로 ML 예측 결과는 직접 시뮬레이션

    else:
        q = st.session_state.query
        st.success(f"✅ '{q['구']}'에서 '{q['업종 중분류']}' 업종으로 {q['인원']}명 기준 추천 맛집")
        
        # '메뉴결정' 탭의 지도와 추천 결과도 동적으로 변경하려면
        # 여기에 LLM/ML 호출 로직을 복사하거나 함수화하여 사용해야 합니다.
        # 현재는 예시용 static 데이터를 사용합니다.
        
        # 예시: LLM/ML 통합 흐름 없이 직접 데이터 생성
        if 'df' not in st.session_state: # df가 로드되지 않았다면 로드 시도
             st.session_state.df = pd.DataFrame({
                "인원": [1, 2, 4, 8, 2, 1, 3, 5, 2, 6, 1],
                "계절": ["여름", "여름", "여름", "여름", "가을", "겨울", "여름", "봄", "여름", "가을", "겨울"],
                "점저": ["점심", "저녁", "저녁", "저녁", "저녁", "점심", "점심", "점심", "저녁", "저녁", "점심"], # '점저'로 통일
                "1인당비용": [15000, 50000, 25000, 37500, 45000, 10000, 12000, 18000, 30000, 22000, 8000],
                "업종 중분류": ["한식", "양식", "중식", "중식", "일식", "한식", "치킨", "한식", "양식", "한식", "분식"],
                "구": ["중구", "중구", "마포구", "마포구", "강남구", "종로구", "마포구", "영등포구", "강남구", "마포구", "중구"],
                "사용장소": [
                    "명동칼국수", "이태원 비스트로", "연남동 중식당", "공덕 회관", 
                    "강남 스시집", "종로 설렁탕", "홍대 치킨집", "여의도 부대찌개",
                    "청담 이탈리안", "합정 삼겹살하우스", "시청 김밥천국"
                ],
                "lat": [37.5630, 37.5348, 37.5580, 37.5450, 37.5170, 37.5700, 37.5560, 37.5210, 37.5250, 37.5502, 37.5650], 
                "lon": [126.9800, 126.9920, 126.9360, 126.9480, 127.0200, 126.9890, 126.9230, 126.9380, 127.0450, 126.9149, 126.9770]
            })

        df = st.session_state.df # 세션 상태에서 df 로드

        filtered_df = df[
            (df['구'] == q['구']) & 
            (df['업종 중분류'] == q['업종 중분류']) &
            (df['점저'] == q['점저'])
        ]
        if not filtered_df.empty:
            # 일치하는 장소가 여러 개라면, 인원 수와 1인당 비용을 고려하여 가장 적합한 것을 선택할 수 있습니다.
            # 여기서는 예시로 첫 번째 일치 항목을 가져옵니다.
            recommended_place = filtered_df.iloc[0].to_dict()
        else:
            # 일치하는 장소가 없을 경우 대체 메시지
            recommended_place = {
                "사용장소": "해당 조건의 추천 맛집을 찾을 수 없습니다.", 
                "lat": 37.5665, "lon": 126.9780, # 기본 서울 시청 좌표
                "구": q['구'], "인원": q['인원'], "1인당비용": q['1인당비용'],
                "점저": q['점저'], "계절": q['계절'], "업종 중분류": q['업종 중분류']
            }


        m = folium.Map(location=[recommended_place['lat'], recommended_place['lon']], zoom_start=15)
        folium.Marker(
            [recommended_place['lat'], recommended_place['lon']],
            popup=f"{recommended_place['사용장소']} - {recommended_place['점저']}에 딱!",
            tooltip=recommended_place['사용장소']
        ).add_to(m)
        st_folium(m, width=800, height=500, key="menu_decision_map") # key 추가

        st.markdown(f"""
        ### 🍽 추천 맛집: {recommended_place['사용장소']}
        - 📍 주소 (구): {recommended_place['구']}
        - 👥 인원: {recommended_place['인원']}
        - 💰 비용: {recommended_place['1인당비용']}
        - ⏰ 시간: {recommended_place['점저']} / {recommended_place['계절']}
        - 🍽 업종: {recommended_place['업종 중분류']}
        """)
        if st.button("🔄 검색 조건 다시 입력하기", key="reset_menu_decision"): # key 추가
            st.session_state.show_input = True
            st.rerun()

# === 지도 보기 ===
elif menu == "지도 보기":
    st.title("🗺️ 현재 위치 보기")
    current_location = [37.5665, 126.9780] # 서울 시청 기준
    m = folium.Map(location=current_location, zoom_start=13)
    folium.Marker(
        location=current_location,
        tooltip="📌 현재위치 (기본값)",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)
    st_folium(m, width=900, height=550)

# === 이용 가이드 ===
elif menu == "이용 가이드":
    st.title("📘 이용 가이드")
    st.markdown("""
    1. 좌측 메뉴에서 '홈' 선택 ➡️ 챗봇을 통해 자유롭게 질문하여 추천받기
    2. 좌측 메뉴에서 '메뉴결정' 선택 ➡️ 정해진 조건으로 세부적인 맛집 추천받기
    3. '지도 보기'에서 현재 설정된 기본 위치 확인
    4. 추천된 장소의 정보와 지도 시각화를 통해 결정하기
    """)

