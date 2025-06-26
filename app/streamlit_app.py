
import streamlit as st
from PIL import Image
import folium
from streamlit_folium import st_folium

# 페이지 설정 (반드시 최상단에서 호출)
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

# === 사이드바 ===
with st.sidebar:
    logo = Image.open("../GongPick/app/logo/gongpicklogo.png")
    st.image(logo, use_column_width=True)
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
                st.session_state.selected_similar = None
                st.session_state.show_response = True
                st.rerun()

    else:
        st.markdown("---")
        if st.button("🔄 다시 질문하기"):
            st.session_state.show_response = False
            st.rerun()

        st.markdown("### 💬 답변")
        st.markdown(f"**'{st.session_state.last_query}'에 대한 추천 결과입니다.**")

        st.markdown("#### 🍽️ 추천 맛집: 삼겹살하우스")
        st.markdown("""
        - 📍 주소: 서울 마포구 합정동 123-45  
        - 👥 인원 추천: 최대 10명  
        - 💰 인당 예산: 12000원  
        - ⭐ 업종: 한식
        """)

        m = folium.Map(location=[37.5502, 126.9149], zoom_start=17)
        folium.Marker(
            location=[37.5502, 126.9149],
            tooltip="삼겹살하우스 🍖",
            popup="서울 마포구 합정동 123-45",
            icon=folium.Icon(color="red", icon="cutlery", prefix="fa")
        ).add_to(m)
        st_folium(m, width=1000, height=600)

        st.markdown("### 🔍 비슷한 장소 추천")
        similar = [
            {"name": "고기짱짱집", "loc": "서울 마포구 성산동 12-34", "emoji": "🥩", "price": "13,000원", "lat": 37.5532, "lon": 126.9175},
            {"name": "합정돼지불백", "loc": "서울 마포구 양화로 22길", "emoji": "🍖", "price": "11,000원", "lat": 37.5491, "lon": 126.9130},
            {"name": "고기나라", "loc": "서울 마포구 홍익로 5길", "emoji": "🍱", "price": "12,500원", "lat": 37.5520, "lon": 126.9210},
        ]

        sim_cols = st.columns(3)
        for i, col in enumerate(sim_cols):
            selected = (st.session_state.selected_similar == i)
            background = "#ffe6e6" if selected else "#f9f9f9"
            border = "2px solid #ff4d4d" if selected else "1px solid #ddd"
            with col:
                if st.button(f"{similar[i]['emoji']} {similar[i]['name']}", key=f"sim_{i}"):
                    st.session_state.selected_similar = i
                    st.rerun()
                st.markdown(f"""
                <div style='border:{border}; border-radius:10px; padding:15px; background-color:{background};'>
                    <p style='margin:0;'>📍 {similar[i]['loc']}</p>
                    <p style='margin:0;'>💰 {similar[i]['price']}</p>
                </div>
                """, unsafe_allow_html=True)

        if st.session_state.selected_similar is not None:
            st.markdown("""
            <script>
            const similarMap = document.getElementById('similar_map');
            if (similarMap) {
                similarMap.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            </script>
            """, unsafe_allow_html=True)

            sel = similar[st.session_state.selected_similar]
            st.markdown("### 📍 선택한 장소 위치")
            st.markdown("<div id='similar_map'></div>", unsafe_allow_html=True)
            m2 = folium.Map(location=[sel["lat"], sel["lon"]], zoom_start=17)
            folium.Marker(
                location=[sel["lat"], sel["lon"]],
                popup=sel["name"],
                tooltip=sel["loc"],
                icon=folium.Icon(color="orange", icon="star", prefix="fa")
            ).add_to(m2)
            st_folium(m2, width=800, height=500)

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
                st.session_state.show_input = False
                st.session_state.query = {
                    "인원": people_count,
                    "계절": season,
                    "시간대": time_slot,
                    "1인당 비용": cost,
                    "업종 중분류": category,
                    "구": district
                }
    else:
        q = st.session_state.query
        st.success(f"✅ '{q['구']}'에서 '{q['업종 중분류']}' 업종으로 {q['인원']}명 기준 추천 맛집")
        m = folium.Map(location=[37.5665, 126.9780], zoom_start=13)
        folium.Marker(
            [37.5665, 126.9780],
            popup="신의주찹쌀순대 - 점심에 딱!",
            tooltip="추천 맛집"
        ).add_to(m)
        st_folium(m, width=800, height=500)
        st.markdown(f"""
        ### 🍽 추천 맛집: 신의주찹쌀순대
        - 📍 주소 (구): {q['구']}
        - 👥 인원: {q['인원']}
        - 💰 비용: {q['1인당 비용']}
        - ⏰ 시간: {q['시간대']} / {q['계절']}
        - 🍽 업종: {q['업종 중분류']}
        """)
        if st.button("🔄 검색 조건 다시 입력하기"):
            st.session_state.show_input = True

# === 지도 보기 ===
elif menu == "지도 보기":
    st.title("🗺️ 현재 위치 보기")
    current_location = [37.5665, 126.9780]
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
    1. 좌측 메뉴에서 참고 질문 선택  
    2. 조건 입력 후 '질문하기' 또는 '맛집 추천 검색' 클릭  
    3. 추천된 장소 확인 + 지도 시각화  
    """)
