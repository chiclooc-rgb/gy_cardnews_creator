import os
import json
import pickle
import google.generativeai as genai
from pathlib import Path
import numpy as np
import tkinter as tk
from tkinter import filedialog
import datetime
import re

# ==========================================
# ⭐⭐⭐ API 키를 여기에 입력하세요 ⭐⭐⭐
GOOGLE_API_KEY = "AIzaSyAIz1XZQdjLmLCqyrK8A_bmvoGi3RxjAP8"
# ==========================================

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "gwangyang_style_index.pkl"

# 모델 설정
genai.configure(api_key=GOOGLE_API_KEY)
embedding_model = 'models/text-embedding-004' # 검색용 저렴한 모델
planning_model = genai.GenerativeModel('gemini-2.5-pro') # 기획용 똑똑한 모델

def load_index():
    """1단계에서 만든 색인 파일을 불러옵니다."""
    if not INDEX_FILE.exists():
        print(f"❌ 오류: 색인 파일을 찾을 수 없습니다 ({INDEX_FILE})")
        print("먼저 build_index.py를 실행해주세요.")
        exit()
    with open(INDEX_FILE, 'rb') as f:
        return pickle.load(f)

def find_best_examples(index, query_text, top_k=3):
    """입력된 텍스트와 가장 비슷한 예시를 색인에서 찾아옵니다 (코사인 유사도)."""
    # 1. 입력 텍스트를 벡터로 변환
    query_embedding = genai.embed_content(
        model=embedding_model,
        content=query_text,
        task_type="retrieval_query"
    )['embedding']
    query_vec = np.array(query_embedding)

    # 2. 유사도 계산
    scores = []
    for entry in index:
        # 코사인 유사도 계산 (간단 버전)
        similarity = np.dot(query_vec, entry['embedding']) / (np.linalg.norm(query_vec) * np.linalg.norm(entry['embedding']))
        scores.append(similarity)
    
    # 3. 상위 Top K개 추출
    top_indices = np.argsort(scores)[-top_k:][::-1]
    
    best_examples = []
    print(f"\n🔍 검색 결과 (Top {top_k}):")
    for i in top_indices:
        data = index[i]['data']
        print(f"- 유사도 {scores[i]:.4f}: {data.get('file_name')} (톤: {data.get('tone_and_manner')})")
        # 기획에 참고할 핵심 정보만 추림
        example_summary = {
            "type": data.get("page_type"),
            "title_style": data.get("main_title"),
            "body_summary_style": data.get("body_summary"),
            "tone": data.get("tone_and_manner")
        }
        best_examples.append(json.dumps(example_summary, ensure_ascii=False))
        
    return "\n".join(best_examples)

def select_notice_file():
    """파일 선택 대화상자를 띄워 공고문 파일을 선택받습니다."""
    root = tk.Tk()
    root.withdraw() # 메인 윈도우 숨김
    file_path = filedialog.askopenfilename(
        title="분석할 공고문 파일(.txt)을 선택하세요",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        initialdir=BASE_DIR
    )
    if file_path:
        return Path(file_path)
    return None

def run_rag_planner():
    print("🚀 [RAG 기반] 스마트 AI 기획자를 실행합니다...")

    # 1. 공고문 파일 선택
    print("📂 분석할 공고문 파일을 선택해주세요 (파일 선택 창이 뜹니다)...")
    notice_file = select_notice_file()

    if not notice_file or not notice_file.exists():
        print("❌ 파일을 선택하지 않았거나 취소했습니다.")
        return
        
    with open(notice_file, 'r', encoding='utf-8') as f:
        source_text = f.read()
    print(f"📄 원문 읽기 완료: {notice_file.name} (길이: {len(source_text)}자)")

    # 2. 색인 로드 및 스마트 검색
    print("📚 스타일 색인을 불러오는 중...")
    index = load_index()
    print("🧐 원문과 가장 유사한 광양시 스타일 예시를 검색합니다...")
    # 원문의 앞부분 일부만 사용하여 검색 쿼리로 활용 (효율성)
    query_text = f"이 공고문의 분위기와 맞는 스타일을 찾아줘: {source_text[:500]}"
    best_examples_context = find_best_examples(index, query_text, top_k=3)

    # 3. 프롬프트 구성 (찾아낸 A급 예시만 보여줌!)
    prompt = f"""
    당신은 광양시청 홍보팀의 수석 카드뉴스 기획자입니다.
    제공된 [원문 공고]를 분석하여 가장 효과적인 카드뉴스 기획안을 작성하세요.

    중요: 아래 제공된 [검색된 유사 스타일 예시]는 이 공고문과 가장 유사한 과거의 우수 사례들입니다. 
    이 예시들의 제목 뽑는 방식, 정보 요약 스타일, 톤앤매너를 적극 참고하여 기획하세요.

    [검색된 유사 스타일 예시 (Top 3)]
    {best_examples_context}

    ---
    [원문 공고]
    {source_text}
    ---

    [지시사항]
    1. **구조 판단:** 원문의 양과 복잡성을 고려하여 스스로 판단하세요.
       - 내용이 짧고 단순하면 -> `SINGLE(1장)` 구조
       - 내용이 많고 복잡하면 -> `MULTI(표지+본문 여러장+마무리)` 구조
    2. **톤앤매너:** 검색된 예시들의 스타일을 반영하여 친근하고 명확하게 작성하세요.
    3. **출력 형식:** 반드시 아래 **순수한 JSON 형식**으로만 출력하세요. (마크다운 제외)

    [출력 JSON 형식 예시]
    {{
      "structure_type": "MULTI",
      "plan": {{
        "cover": {{ "main_title": "...", "sub_title": "..." }},
        "body": [ {{ "page": 1, "summary": ["..."] }}, ... ],
        "outro": {{ "contact": "..." }}
      }},
      "estimated_tone": "(예: 활기찬, 정보성)"
    }}
    """

    print("\n🧠 AI가 검색된 예시를 참고하여 기획안을 작성 중입니다... (비용 절약 중!)")
    
    try:
        # 4. API 호출 (가장 똑똑한 Gemini 2.5 Pro 사용)
        response = planning_model.generate_content(prompt)
        response_text = response.text.strip()
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        
        plan_data = json.loads(response_text)
        
        print("\n" + "="*60)
        print("🎉 [RAG 기획 성공] 스마트 기획안이 완성되었습니다!")
        print("="*60)
        print(json.dumps(plan_data, indent=2, ensure_ascii=False))
        print("="*60)

        # 5. 결과 저장 (카드뉴스 문안 폴더)
        OUTPUT_DIR = BASE_DIR / "카드뉴스 문안"
        OUTPUT_DIR.mkdir(exist_ok=True)

        # 제목 추출 및 파일명 생성
        try:
            title = plan_data["plan"]["cover"]["main_title"]
            # 파일명에 쓸 수 없는 문자 제거
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        except:
            safe_title = "제목없음"

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        filename = f"{today} {safe_title}.json"
        output_path = OUTPUT_DIR / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 기획안이 저장되었습니다: {output_path}")
        print("👉 이 기획안은 '검색된 최적의 예시'를 기반으로 작성되어 품질이 높고 비용은 저렴합니다.")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        # print(f"응답 원문: {response.text}")

if __name__ == "__main__":
    # numpy 설치 필요
    try:
        import numpy
    except ImportError:
        os.system("pip install numpy")
        import numpy
        
    run_rag_planner()
