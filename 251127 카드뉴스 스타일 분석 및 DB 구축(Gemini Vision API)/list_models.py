import google.generativeai as genai
import os

API_KEY = "AIzaSyAIz1XZQdjLmLCqyrK8A_bmvoGi3RxjAP8"
genai.configure(api_key=API_KEY)

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
