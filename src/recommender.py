import pickle
from sklearn.cluster import KMeans

def train_model(data):
    model = KMeans(n_clusters=5)
    model.fit(data)
    with open("models/recommender.pkl", "wb") as f:
        pickle.dump(model, f)

def predict(model, input_data):
    return model.predict([input_data])[0]

def load_model():
    with open("models/recommender.pkl", "rb") as f:
        return pickle.load(f)