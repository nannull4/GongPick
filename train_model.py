import pandas as pd
from src.recommender import train_model

# 주소지를 숫자로 매핑 (간단 예시)
def get_region_code(addr):
    if "종로" in addr:
        return 1
    elif "강남" in addr:
        return 2
    else:
        return 3

# CSV 불러오기
df = pd.read_csv("data/data.csv")
df = df.dropna(subset=["1인당비용", "주소지"])

# 전처리
df["지역코드"] = df["주소지"].apply(get_region_code)
X = df[["1인당비용", "지역코드"]]

# 모델 학습 및 저장
train_model(X)
print("✅ 모델 학습 완료 및 recommender.pkl 생성됨")
