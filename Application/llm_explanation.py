import os
import requests
import numpy as np

API_KEY = os.getenv("MISTRAL_API_KEY", "xGbwkJFTpe7BpsA0iyH462sYW8QPXFNs")
MODEL = "mistral-tiny"
API_URL = "https://api.mistral.ai/v1/chat/completions"


def mistral_chat(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }

    resp = requests.post(API_URL, headers=headers, json=data)
    if resp.status_code != 200:
        return f"LLM Error: {resp.text}"

    return resp.json()["choices"][0]["message"]["content"]


def build_prompt(result_json):
    state = result_json["Predicted Class"]
    prob = result_json["Prediction Probability"]

    importance = result_json["details"][0]["magnitude"]
    feature_order = ["EAR", "PUC", "MAR", "MOE"]

    importance_text = "\n".join([
        f"{k}: {float(importance[k]):.6e}"
        for k in feature_order
    ])

    prompt = f"""
You are an empathetic in-car safety assistant. Your job is to give ONE short message to the driver based ONLY on the model’s output below.

Model Output:
Predicted class: {state}
Prediction probability: {prob}

IMPORTANT INSTRUCTIONS:
- You MUST give a message ONLY for the predicted class shown above.
- NEVER list multiple stages.
- NEVER describe all possible conditions.
- NEVER mention any numbers, probabilities, thresholds, or internal values.
- NEVER mention the feature importance values.
- NEVER explain how the classifier works.
- NEVER put the answer inside quotes.
- NEVER start or end the text with quotation marks.
- NEVER start the answer with the predicted class.

Your tone rules (follow exactly):
- If predicted class is alert: give a brief, calm confirmation and STOP.
- If slightly drowsy: give a gentle suggestion to consider resting soon.
- If very drowsy: give a firm warning to slow down and rest immediately.
- If critical drowsiness: give an urgent command to pull over right now. No soft language.

Only for critical drowsiness, If the driver thinks the system is mistaken, tell them they may press the cancel button.

Keep your response:
- short
- human
- realistic
- focused ONLY on the predicted class
"""

    return prompt


def generate_explanation(result_json):
    prompt = build_prompt(result_json)
    return mistral_chat(prompt)