from transformers import pipeline

classifier = pipeline("sentiment-analysis")

def analyze(text):
    result = classifier(text)[0]
    label = result["label"]
    score = result["score"]
    return score if label == "POSITIVE" else 1 - score