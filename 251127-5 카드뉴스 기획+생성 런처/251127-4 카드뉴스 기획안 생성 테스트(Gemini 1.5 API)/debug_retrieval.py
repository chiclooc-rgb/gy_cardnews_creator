import pickle
import google.generativeai as genai
import numpy as np
from pathlib import Path
import os

# API Key (reused from test_planner_rag.py)
GOOGLE_API_KEY = "AIzaSyAIz1XZQdjLmLCqyrK8A_bmvoGi3RxjAP8"
genai.configure(api_key=GOOGLE_API_KEY)
embedding_model = 'models/text-embedding-004'

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "gwangyang_style_index.pkl"

def load_index():
    if not INDEX_FILE.exists():
        print(f"❌ Index file not found: {INDEX_FILE}")
        return None
    with open(INDEX_FILE, 'rb') as f:
        return pickle.load(f)

def find_best_examples(index, query_text, top_k=5):
    print(f"\n🔎 Query: {query_text}")
    query_embedding = genai.embed_content(
        model=embedding_model,
        content=query_text,
        task_type="retrieval_query"
    )['embedding']
    query_vec = np.array(query_embedding)

    scores = []
    for entry in index:
        similarity = np.dot(query_vec, entry['embedding']) / (np.linalg.norm(query_vec) * np.linalg.norm(entry['embedding']))
        scores.append(similarity)
    
    top_indices = np.argsort(scores)[-top_k:][::-1]
    
    results = []
    for i in top_indices:
        data = index[i]['data']
        print(f"- Score {scores[i]:.4f}: {data.get('file_name')}")
        print(f"  Tone: {data.get('tone_and_manner')}")
        print(f"  Vibe: {data.get('visual_vibe')}")
        print(f"  Keywords: {data.get('keywords')}")
        results.append(data)
    return results

if __name__ == "__main__":
    try:
        import numpy
    except ImportError:
        os.system("pip install numpy")
        import numpy

    index = load_index()
    if index:
        # Test Case 1: Generic Notice
        find_best_examples(index, "이 공고문의 분위기와 맞는 스타일을 찾아줘: 2025년 광양시 청년 주택 자금 대출 이자 지원 사업 공고")
        
        # Test Case 2: Event/Festival
        find_best_examples(index, "이 공고문의 분위기와 맞는 스타일을 찾아줘: 제24회 광양 매화 축제 개최 안내")
        
        # Test Case 3: Serious/Warning
        find_best_examples(index, "이 공고문의 분위기와 맞는 스타일을 찾아줘: 산불 조심 기간 운영 및 과태료 부과 안내")
