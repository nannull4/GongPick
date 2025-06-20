import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from src.recommender import predict, load_model
from src.sentiment import analyze

model = load_model()

st.title("🍽️ 공무원 맛집 추천기")

budget = st.number_input("예산 (원)")
region_code = st.selectbox("지역 코드", [1, 2, 3])
review = st.text_area("식당 리뷰 (선택)")

if st.button("추천 받기"):
    sentiment_weight = analyze(review) if review else 1.0
    cluster = predict(model, [budget, region_code])
    st.success(f"추천 클러스터: {cluster} (신뢰도 보정: {sentiment_weight:.2f})")