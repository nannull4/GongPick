import streamlit as st
from PIL import Image
from pathlib import Path 
import folium
from streamlit_folium import st_folium
import os, joblib, pandas as pd
from dotenv import load_dotenv 
from openai import AzureOpenAI
import json
import streamlit.components.v1 as components
# 환경변수 로드
load_dotenv()

BASE_DIR   = Path(__file__).resolve().parents[1]      # GongPick/
MODEL_PATH = Path(os.getenv("MODEL_PATH", BASE_DIR / "outputs" / "gongpick.pkl"))
RAW_PATH   = Path(os.getenv("RAW_DATA_PATH", BASE_DIR / "data" / "raw" / "프렌차이즈_구추출_결과 1.csv"))

# --- 페이지 설정 ---
st.set_page_config(page_title="공무원 맛집 추천 시스템", layout="wide")

@st.cache_resource(show_spinner=False)
def load_resources():
    try:
        # 환경변수 기반 경로 우선, 없으면 기본 경로 사용
        model_path = MODEL_PATH if MODEL_PATH.exists() else Path("ML_model.pkl")
        model = joblib.load(model_path)
        
        # 원본 데이터 로드 (있는 경우)
        raw = None
        if RAW_PATH.exists():
            raw = pd.read_csv(RAW_PATH, encoding="utf-8")
        
        return model, raw
    except FileNotFoundError as e:
        st.error(f"모델 파일을 찾을 수 없습니다: {e}")
        st.stop()
    except Exception as e:
        st.error(f"리소스 로드 중 오류 발생: {e}")
        st.stop()

pipeline, raw_df = load_resources()

# ───────── 로고 경로 ─────────
APP_DIR  = Path(__file__).resolve().parent              # app/
LOGO_PATH = APP_DIR / "logo" / "gongpicklogo.png" 

# --- Azure OpenAI 설정 ---
azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
your_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

# AzureOpenAI 클라이언트 초기화
try:
    client = AzureOpenAI(
        api_key=azure_openai_api_key,
        azure_endpoint=azure_openai_endpoint,
        api_version=azure_openai_api_version
    )
    # st.success("Azure OpenAI 클라이언트가 성공적으로 초기화되었습니다.")
except Exception as e:
    st.error(f"Azure OpenAI 클라이언트 초기화 오류: {e}")
    st.stop()

# --- 시스템 프롬프트 정의 ---
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

# --- 서비스 지원 지역 리스트 ---
valid_korean_districts = [
    "마포구", "관악구", "은평구", "중구"
]

# --- 예시 데이터프레임 초기화 ---
def initialize_sample_data():
    """샘플 데이터 초기화 (실제 데이터가 없는 경우)"""
    return pd.DataFrame({
        "인원": [1, 2, 4, 8, 2, 1, 3, 5, 2, 6, 1],
        "계절": ["여름", "여름", "여름", "여름", "가을", "겨울", "여름", "봄", "여름", "가을", "겨울"],
        "점저": ["점심", "저녁", "저녁", "저녁", "저녁", "점심", "점심", "점심", "저녁", "저녁", "점심"],
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

# 데이터프레임 초기화
if 'df' not in st.session_state:
    if raw_df is not None:
        st.session_state.df = raw_df
    else:
        st.session_state.df = initialize_sample_data()



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
if "llm_parsed_data" not in st.session_state:
    st.session_state.llm_parsed_data = {}
if "predicted_place_info" not in st.session_state:
    st.session_state.predicted_place_info = {}
if "similar_places_info" not in st.session_state:
    st.session_state.similar_places_info = []
if "selected_similar_menu" not in st.session_state:
    st.session_state.selected_similar_menu = None

# === 사이드바 ===
with st.sidebar:
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH)     
        st.image(logo, use_container_width=True)
    else:
        st.markdown("### 🍽️ GongPick")
    st.markdown("<p style='color: rgba(128, 144, 182, 1); font-weight: bold;'>공무원들의 믿을만한 Pick!</p>", unsafe_allow_html=True)
    st.markdown("#### 오늘의 업무도 맛있게!")
    menu = st.radio("📋 메뉴", ["홈", "메뉴결정"], index=0)
    # menu = st.radio("📋 메뉴", ["홈", "메뉴결정", "지도 보기", "이용 가이드"], index=0)

# === 홈 (챗봇) ===
if menu == "홈":
    st.markdown("<div id='top'></div>", unsafe_allow_html=True)

    if not st.session_state.show_response:
        # --- Custom CSS for styling ---
        st.markdown("""
            <style>
                /* Hero Section */
                .hero-section {
                    padding: 3rem 1rem;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    border-radius: 15px;
                    text-align: center;
                    margin-bottom: 2.5rem;
                }
                .hero-section h1 {
                    font-weight: 900;
                    font-size: 3.5rem;
                    color: #1e3a8a; /* Deep Blue */
                    margin-bottom: 0.5rem;
                    letter-spacing: -2px;
                }
                .hero-section p {
                    color: #3e4c59;
                    font-size: 1.2rem;
                    max-width: 650px;
                    margin: auto;
                }

                /* Example Questions Section */
                .examples-section h2 {
                    color: #1e3a8a;
                    font-weight: bold;
                    text-align: center;
                    margin-bottom: 1.5rem;
                }

                /* Style for the cards to ensure uniform height */
                .example-card {
                    height: 100%;
                    border: 1px solid #EAECEF; /* Add border here */
                    border-radius: 15px;
                    padding: 15px; /* Add padding here */
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05); /* Add shadow here */
                    transition: all 0.2s ease-in-out; /* Add transition for hover */
                }
                .example-card:hover {
                    transform: translateY(-3px); /* Lift effect on hover */
                    box-shadow: 0 6px 15px rgba(0,0,0,0.08); /* Stronger shadow on hover */
                }
                .example-card > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                }

                /* Chat Input Form */
                .stForm {
                    background-color: #FFFFFF;
                    padding: 2rem 2rem 1rem 2rem;
                    border-radius: 15px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                    margin-top: 2rem;
                }
                .stForm [data-testid="stFormSubmitButton"] button {
                    width: 100%;
                    background-color: #16a34a; /* Green-600 */
                    font-size: 1.1rem;
                    font-weight: bold;
                }
                .stForm [data-testid="stFormSubmitButton"] button:hover {
                    background-color: #15803d; /* Green-700 */
                }
                .similar-places-heading {
                    margin-top: 2.5rem; /* Spacing from the map */
                    margin-bottom: 1.5rem;
                    color: #1e3a8a;
                    font-weight: bold;
                }
            </style>
        """, unsafe_allow_html=True)

        # --- Hero Section ---
        st.markdown("""
            <div class='hero-section'>
                <h1>Gong-Bot 🤖</h1>
                <p><strong>🍕배는 고픈데 결정은 못하겠다면❓ Gong bot 부르세요</strong><br>
                간단하게 질문하거나 아래 예시를 눌러보세요‼️</p>
            </div>
        """, unsafe_allow_html=True)

        # --- Example Questions ---
        with st.container():
            st.markdown("<div class='examples-section'><h2>✨ 이렇게 물어보세요!</h2></div>", unsafe_allow_html=True)
            
            example_questions = [
                (" 점심 회식 💼", "마포구에서 점심 먹을 건데 추천해줘 인당 12000"),
                (" 저녁 회식 🍻", "8명이 저녁에 회식할 건데 중식집으로 부탁해"),
                (" 데이트 ❤️", "여자친구랑 데이트 갈건데 중식집으로 추천해줘") # Added back
            ]
            
            cols = st.columns(3) # Changed back to 3
            for i, col in enumerate(cols):
                with col:
                    with st.container(): # Removed border=True
                        st.markdown(f"<h4 style='text-align: center;'>{example_questions[i][0]}</h4>", unsafe_allow_html=True)
                        if st.button(f"{example_questions[i][1]}", key=f"ex_{i}", use_container_width=True):
                            st.session_state.chat_input = example_questions[i][1]
                            st.session_state.show_response = False # Ensure response section is hidden
                            # Clear previous results when an example is clicked
                            st.session_state.predicted_place_info = {}
                            st.session_state.similar_places_info = []
                            st.session_state.llm_parsed_data = {}
                    st.markdown("</div>", unsafe_allow_html=True)

        # --- Chat Input Form ---
        with st.form("chat_form"):
            user_query = st.text_input(
                "💬 **직접 질문하기**",
                value=st.session_state.chat_input,
                key="chat_input_box",
                placeholder="예: 강남에서 3명이서 먹을만한 파스타집 알려줘"
            )
            
            submitted = st.form_submit_button("🚀 추천 받기!", use_container_width=True)

            if submitted and user_query:
                st.session_state.last_query = user_query
                st.session_state.chat_input = user_query
                st.session_state.selected_similar = None
                st.session_state.show_response = True
                # 이전 결과 초기화
                st.session_state.predicted_place_info = {}
                st.session_state.similar_places_info = []
                st.session_state.llm_parsed_data = {}
                st.rerun()

    else: # 질문 제출 후
        st.markdown("---")
        if st.button("🔄 다시 질문하기"):
            st.session_state.show_response = False
            st.rerun()

        st.markdown("### 💬 답변")
        st.markdown(f"**'{st.session_state.last_query}'에 대한 추천 결과입니다.**")

        # --- LLM 및 ML 모델 로직 (결과가 없을 때만 실행) ---
        if not st.session_state.predicted_place_info:
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
                            {"role": "user", "content": st.session_state.last_query}
                        ],
                        max_tokens=200,
                        response_format={"type": "json_object"}
                    )

                    llm_output_json_str = response.choices[0].message.content
                    model_input_data = json.loads(llm_output_json_str)
                    st.session_state.llm_parsed_data = model_input_data

                    # 서비스 미지원 지역 검사
                    extracted_gu = model_input_data.get("구")

                    if extracted_gu and extracted_gu not in valid_korean_districts:
                        st.error(f"🚨 서비스 미지원 지역입니다: **'{extracted_gu}'**.\n\n"
                                 "대한민국 서울특별시 내의 '구' 단위 지역만 지원됩니다. 다시 질문해주세요.")
                    else:
                        st.success(f"✅ '{extracted_gu}'는 지원되는 지역입니다. ML 모델 예측을 시작합니다.")
                        
                        # ML 모델 입력 데이터 준비 및 예측
                        feature_columns = ["인원", "계절", "점저", "1인당비용", "업종 중분류", "구"]
                        
                        if not all(field in model_input_data for field in feature_columns):
                            st.error("LLM 출력에 ML 모델 예측에 필요한 필수 필드가 누락되었습니다. 다시 질문해주세요.")
                        else:
                            # 숫자형 필드 타입 변환
                            try:
                                model_input_data["인원"] = int(model_input_data["인원"])
                                model_input_data["1인당비용"] = int(model_input_data["1인당비용"])
                            except ValueError:
                                st.error("LLM이 반환한 '인원' 또는 '1인당비용' 값이 유효한 숫자가 아닙니다. 다시 질문해주세요.")
                                st.stop()

                            # ML 모델에 전달할 DataFrame 생성
                            example = pd.DataFrame([model_input_data], columns=feature_columns)
                            
                            try:
                                predicted_probs = pipeline.predict_proba(example)
                                predicted_class_index = predicted_probs.argmax()
                                predicted_place_name = pipeline.classes_[predicted_class_index]
                                confidence = predicted_probs[0][predicted_class_index]

                                # 예측된 장소 정보 가져오기
                                df = st.session_state.df
                                predicted_place_row = df[df['사용장소'] == predicted_place_name]
                                
                                if not predicted_place_row.empty:
                                    predicted_place_row = predicted_place_row.iloc[0]
                                    # 위경도 정보가 있는지 확인
                                    if 'lat' in predicted_place_row and 'lon' in predicted_place_row:
                                        lat, lon = predicted_place_row['lat'], predicted_place_row['lon']
                                    else:
                                        # 기본 위치 설정 (서울 시청)
                                        lat, lon = 37.5665, 126.9780
                                    
                                    st.session_state.predicted_place_info = {
                                        "name": predicted_place_row['사용장소'],
                                        "address": f"서울 {predicted_place_row['구']} ",
                                        "lat": lat,
                                        "lon": lon,
                                        "people_rec": "최대 10명",
                                        "cost_per_person": predicted_place_row['1인당비용'],
                                        "category": predicted_place_row['업종 중분류']
                                    }

                                    # 동일 업종 중분류 및 구 내 비슷한 장소 3개 추천
                                    similar_places_df = df[(df['업종 중분류'] == st.session_state.predicted_place_info['category']) & 
                                                           (df['구'] == model_input_data['구']) &
                                                           (df['사용장소'] != st.session_state.predicted_place_info['name'])]
                                    
                                    num_similars = min(3, len(similar_places_df))
                                    if num_similars > 0:
                                        st.session_state.similar_places_info = similar_places_df.sample(n=num_similars).to_dict(orient='records')
                                    else:
                                        st.session_state.similar_places_info = []

                                else:
                                    st.warning(f"예측된 장소 '{predicted_place_name}'에 대한 상세 정보를 찾을 수 없습니다.")

                            except Exception as ml_e:
                                st.error(f"ML 모델 예측 중 오류 발생: {ml_e}")

                except json.JSONDecodeError:
                    st.error("❌ LLM 출력 JSON 파싱 오류. 다시 질문해주세요.")
                except Exception as e:
                    st.error(f"⚠️ API 호출 또는 처리 중 오류 발생: {e}. 다시 질문해주세요.")

        # --- 결과 표시 (매번 실행) ---
        if st.session_state.predicted_place_info:
            st.markdown(f"#### 🍽️ 추천 맛집: {st.session_state.predicted_place_info['name']}")
            st.markdown(f"""
                - 📍 주소: {st.session_state.predicted_place_info['address']}
                - 👥 인원 추천: {st.session_state.predicted_place_info['people_rec']}
                - 💰 인당 예산: {st.session_state.predicted_place_info['cost_per_person']}원 
                - ⭐ 업종: {st.session_state.predicted_place_info['category']}
            """)
            # st.write(f"_(신뢰도: {confidence:.2%})_") # confidence는 계산 블록 안에 있어 직접 접근 불가

            # 지도 표시
            m = folium.Map(location=[st.session_state.predicted_place_info['lat'], st.session_state.predicted_place_info['lon']], zoom_start=17)
            folium.Marker(
                location=[st.session_state.predicted_place_info['lat'], st.session_state.predicted_place_info['lon']],
                tooltip=st.session_state.predicted_place_info['name'],
                popup=st.session_state.predicted_place_info['address'],
                icon=folium.Icon(color="red", icon="cutlery", prefix="fa")
            ).add_to(m)
            st_folium(m, width=1000, height=600, key="predicted_map")

            st.markdown("<h3 class='similar-places-heading'>🔍 비슷한 장소 추천</h3>", unsafe_allow_html=True)
            
            if st.session_state.similar_places_info:
                sim_cols = st.columns(len(st.session_state.similar_places_info))
                for i, sim_place in enumerate(st.session_state.similar_places_info):
                    with sim_cols[i]:
                        with st.container(border=True):
                            st.markdown(f"""
                                <div class="similar-card-content">
                                    <h5 style="font-weight:bold; text-align:center;">{sim_place['사용장소']}</h5>
                                    <p style="margin:0; text-align:center;">📍 {sim_place['구']}</p>
                                    <p style="margin:0; text-align:center;">💰 {sim_place['1인당비용']}원</p>
                                </div>
                            """, unsafe_allow_html=True)
                            if st.button("자세히 보기", key=f"sim_{i}", use_container_width=True):
                                st.session_state.selected_similar = i
                                st.rerun()
            else:
                st.info("비슷한 추천 장소를 찾을 수 없습니다.")

            if st.session_state.selected_similar is not None and st.session_state.similar_places_info:
                sel = st.session_state.similar_places_info[st.session_state.selected_similar]
                st.markdown("### 📍 선택한 장소 위치")
                st.markdown("<div id='similar_map'></div>", unsafe_allow_html=True)
                # 위경도 정보 확인
                if 'lat' in sel and 'lon' in sel:
                    sel_lat, sel_lon = sel["lat"], sel["lon"]
                else:
                    sel_lat, sel_lon = 37.5665, 126.9780  # 기본 위치
                
                m2 = folium.Map(location=[sel_lat, sel_lon], zoom_start=17)
                folium.Marker(
                    location=[sel_lat, sel_lon],
                    popup=sel["사용장소"],
                    tooltip=f"{sel['사용장소']} ({sel['구']})",
                    icon=folium.Icon(color="orange", icon="star", prefix="fa")
                ).add_to(m2)
                st_folium(m2, width=800, height=500, key="similar_map_display")

        st.markdown("""
        <div style="text-align: right; margin-top: 20px;">
            <a href="#top" style="font-weight: bold; text-decoration: none; font-size: 18px;">🔝 맨 위로</a>
        </div>
        """, unsafe_allow_html=True)

# === 메뉴결정 ===
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
                # 1) 사용자가 입력한 값을 모델 feature와 같은 컬럼명으로 변환
                query_row = {
                    "인원": people_count,
                    "계절": season,
                    "점저": time_slot,              # ⚠️ 학습 컬럼명이 '점저' 였죠!
                    "1인당비용": int(cost),
                    "업종 중분류": category,
                    "구": district
                }
                query_df = pd.DataFrame([query_row])
 
                # 2) 예측
                proba = pipeline.predict_proba(query_df)
                idx   = proba.argmax()
                place = pipeline.classes_[idx]
                conf  = proba[0][idx]
 
                # 3) 같은 업종 중분류 내 유사 장소 3개
                sim_places = (raw_df[(raw_df["업종 중분류"] == category)
                                    & (raw_df["사용장소"] != place)]
                            ["사용장소"].value_counts().head(3).index.tolist())
 
                # 4) 세션에 저장하고 결과표시로 전환
                st.session_state.show_input = False
                st.session_state.query = {**query_row,
                                        "pred_place": place,
                                        "pred_conf": conf,
                                        "sim_places": sim_places}
                st.rerun()
    else:
        q = st.session_state.query
 
        st.success(f"✅ {q['구']} · {q['업종 중분류']} · {q['인원']}명 기준 추천")
 
        # ── 지도: 원본 데이터에 위·경도 컬럼이 있다면 활용 ──
        if raw_df is not None:
            loc_row = raw_df[raw_df["사용장소"] == q["pred_place"]]
            if not loc_row.empty and {"위도", "경도"}.issubset(loc_row.columns):
                lat, lon = loc_row.iloc[0]["위도"], loc_row.iloc[0]["경도"]
            else:
                lat, lon = 37.5665, 126.9780      # 위·경도 없으면 서울 시청 기준
        else:
            lat, lon = 37.5665, 126.9780
 
        m = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker([lat, lon],
                    popup=q["pred_place"],
                    tooltip=f"{q['pred_place']} ({q['pred_conf']:.0%})",
                    icon=folium.Icon(color="red")).add_to(m)
        m_html = m.get_root().render()
        components.html(m_html, height=500, width=800)
 
 
        # ── 상세 정보 ──
        st.markdown(f"""
        ### 🍽 추천 맛집: **{q['pred_place']}**
        - 📍 구: {q['구']}
        - 👥 인원: {q['인원']}
        - 💰 1인당 비용: {q['1인당비용']}원
        - ⏰ {q['계절']} · {q['점저']}
        - ⭐ 업종: {q['업종 중분류']}
        """)
 
        # ── 유사 장소 ──
        if q["sim_places"]:
            st.markdown("#### 🔍 비슷한 장소")
            for i, p in enumerate(q["sim_places"]):
                if st.button(f"📍 {p}", key=f"sim_menu_{i}"):
                    st.session_state.selected_similar_menu = p
                    st.rerun()

        if st.session_state.selected_similar_menu:
            st.markdown(f"### 🗺️ {st.session_state.selected_similar_menu} 위치")
            sim_loc_row = raw_df[raw_df["사용장소"] == st.session_state.selected_similar_menu]
            if not sim_loc_row.empty and {"위도", "경도"}.issubset(sim_loc_row.columns):
                sim_lat, sim_lon = sim_loc_row.iloc[0]["위도"], sim_loc_row.iloc[0]["경도"]
            else:
                sim_lat, sim_lon = 37.5665, 126.9780
            
            m2 = folium.Map(location=[sim_lat, sim_lon], zoom_start=15)
            folium.Marker([sim_lat, sim_lon], popup=st.session_state.selected_similar_menu).add_to(m2)
            st_folium(m2, width=800, height=500, key="similar_map_menu")

 
        if st.button("🔄 검색 조건 다시 입력하기"):
            st.session_state.show_input = True
            st.session_state.selected_similar_menu = None
            st.rerun()

# === 지도 보기 ===
# elif menu == "지도 보기":
#     st.title("🗺️ 현재 위치 보기")
#     current_location = [37.5665, 126.9780]
#     m = folium.Map(location=current_location, zoom_start=13)
#     folium.Marker(
#         location=current_location,
#         tooltip="📌 현재위치 (기본값)",
#         icon=folium.Icon(color="blue", icon="info-sign")
#     ).add_to(m)
#     st_folium(m, width=900, height=550)
 
# # === 이용 가이드 ===
# elif menu == "이용 가이드":
#     st.title("📘 이용 가이드")
#     st.markdown("""
#     1. 좌측 메뉴에서 참고 질문 선택  
#     2. 조건 입력 후 '질문하기' 또는 '맛집 추천 검색' 클릭  
#     3. 추천된 장소 확인 + 지도 시각화  
#     """)

    