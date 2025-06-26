import streamlit as st
from PIL import Image
import folium
from streamlit_folium import st_folium
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="공무원 맛집 추천 시스템", layout="wide")

# === 사이드바 ===
with st.sidebar:
    logo = Image.open("../GongPick/app/logo/gongpicklogo.png")
    st.image(logo, use_column_width=True)

    st.markdown(
        "<p style='color: rgba(128, 144, 182, 1); font-weight: bold;'>공무원들의 믿을만한 Pick!</p>",
        unsafe_allow_html=True
    )
    st.markdown("#### 오늘의 업무도 맛있게!")
    menu = st.radio("📋 메뉴", ["홈", "챗봇 상담", "지도 보기", "이용 가이드"])

# 초기 상태 저장
if "show_input" not in st.session_state:
    st.session_state.show_input = True
if "query" not in st.session_state:
    st.session_state.query = {}

# === 메뉴별 화면 ===
if menu == "홈":
    st.title("🍱 공무원 맞춤형 맛집 추천 시스템")

    # 입력 폼
    if st.session_state.show_input:
        with st.form("input_form"):
            st.subheader("🔍 집행 정보 입력")
            col1, col2 = st.columns(2)
            with col1:
                purpose = st.text_input("📌 집행 목적")
                people = st.selectbox("👥 인원 수", ["1명", "2명", "3명", "4명 이상"])
                season = st.radio("🍂 계절", ["봄", "여름", "가을", "겨울"])
                cost = st.selectbox("💰 1인당 비용", ["5천원 미만", "5천~1만원", "1만원~2만원", "2만원 이상"])
            with col2:
                address = st.text_input("📍 주소지 또는 행정동")
                category = st.selectbox("🍽 업종 분류", ["한식", "중식", "일식", "양식", "기타"])
                time_slot = st.radio("⏰ 식사 시간", ["점심", "저녁"])
                exec_date = st.date_input("📅 집행 날짜", value=datetime.today().date())
                exec_time = st.time_input("🕒 집행 시간", value=datetime.now().time())

            submitted = st.form_submit_button("🔎 맛집 추천 검색")

            if submitted:
                st.session_state.show_input = False
                st.session_state.query = {
                    "목적": purpose,
                    "인원": people,
                    "계절": season,
                    "1인당 비용": cost,
                    "주소": address,
                    "업종": category,
                    "시간대": time_slot,
                    "일시": datetime.combine(exec_date, exec_time)
                }

    # 추천 결과 화면
    else:
        q = st.session_state.query
        st.success(f"✅ '{q['주소']}'에서 '{q['업종']}' 업종으로 {q['인원']} 기준 추천 맛집")

        # 지도
        m = folium.Map(location=[37.5665, 126.9780], zoom_start=13)
        folium.Marker(
            [37.5665, 126.9780],
            popup="신의주찹쌀순대 - 점심에 딱!",
            tooltip="추천 맛집"
        ).add_to(m)
        st_folium(m, width=800, height=500)

        # 상세 내용
        st.markdown(f"""
        ### 🍽 추천 맛집: 신의주찹쌀순대
        - 📍 주소: {q['주소']}
        - 👥 인원: {q['인원']}
        - 💰 비용: {q['1인당 비용']}
        - 🕒 시간: {q['시간대']} / {q['계절']}
        - 📅 일시: {q['일시'].strftime('%Y-%m-%d %H:%M')}
        """)

        if st.button("🔄 검색 조건 다시 입력하기"):
            st.session_state.show_input = True

elif menu == "챗봇 상담":
    st.title("🤖 챗봇 상담")
    user_query = st.text_input("추천 맛집에 대해 궁금한 점을 입력하세요:", placeholder="예: '신의주찹쌀순대는 어떤 곳인가요?'")
    if st.button("질문하기"):
        st.success(f"챗봇 응답 (예시): '{user_query}'에 대해 자세히 설명드릴게요!")

elif menu == "지도 보기":
    st.title("🗺️ 지도 보기")
    m = folium.Map(location=[37.5663, 126.9014], zoom_start=13)

    # 귀여운 마커 아이콘 (색상, 아이콘 종류 설정)
    marker = folium.Marker(
        location=[37.5663, 126.9014],
        tooltip="📌현재위치",
        icon=folium.Icon(color="pink", icon="cutlery", prefix="fa")  # font-awesome 아이콘
    )

    marker.add_to(m)

    # Streamlit에서 출력
    from streamlit_folium import st_folium
    st_folium(m, width=800, height=500)
elif menu == "이용 가이드":
    st.title("📘 이용 가이드")
    st.markdown("""
    1. 좌측에서 **입력폼** 작성
    2. '맛집 추천 검색' 클릭
    3. 추천된 장소 확인 + 지도 시각화
    4. 챗봇 또는 지도 보기로 이동 가능
    """)


