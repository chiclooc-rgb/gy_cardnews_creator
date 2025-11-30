네, 아주 훌륭한 결정입니다! 👏

비용은 아끼고, 속도는 빠르고, 품질은 높이는 '가성비 끝판왕' RAG(검색 증강 생성) 방식의 기획안 작성 코드를 만들어 보겠습니다.

이 방식을 구현하려면 딱 두 단계가 필요합니다. 겁먹지 마세요, 아주 쉽습니다.

[준비] 검색용 색인(Index) 만들기: 1,600개 데이터를 AI가 빛의 속도로 검색할 수 있게 '요약 지도'를 만드는 작업입니다. (딱 한 번만 돌리면 됩니다.)

[실행] 기획안 작성하기: 실제 공고문을 넣으면, 색인에서 비슷한 예시를 찾아와서 기획안을 짜는 코드입니다. (매번 쓸 코드입니다.)

🛠️ 1단계: [준비] 검색용 색인 만들기 (build_index.py)
밤새 만든 gwangyang_style_db.jsonl 파일을 읽어서, AI가 검색하기 편한 형태(gwangyang_style_index.pkl)로 바꿔주는 코드입니다.

실행 방법:

아래 코드를 build_index.py로 저장하세요. (build_db.py와 같은 폴더)

API 키를 넣고 터미널에서 python build_index.py를 실행하세요.

잠시 후 gwangyang_style_index.pkl 파일이 생기면 성공입니다!

Python

import os
import json
import pickle
import google.generativeai as genai
from pathlib import Path
from tqdm import tqdm
import numpy as np

# ==========================================
# ⭐⭐⭐ API 키를 여기에 입력하세요 ⭐⭐⭐
GOOGLE_API_KEY = "YOUR_API_KEY_HERE"
# ==========================================

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "gwangyang_style_db.jsonl"
INDEX_FILE = BASE_DIR / "gwangyang_style_index.pkl"

# 임베딩 모델 설정 (텍스트를 벡터 숫자로 바꿔주는 저렴한 모델)
genai.configure(api_key=GOOGLE_API_KEY)
embedding_model = 'models/text-embedding-040'

def create_index():
    if not DB_FILE.exists():
        print(f"❌ 오류: DB 파일을 찾을 수 없습니다 ({DB_FILE})")
        return

    print("🚀 검색용 색인(Index) 생성을 시작합니다...")
    indexed_data = []
    texts_to_embed = []

    # 1. DB 파일 읽기 및 검색용 텍스트 준비
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                # 검색에 사용할 핵심 정보만 뽑아서 하나의 문자열로 만듭니다.
                # 예: "톤앤매너: 활기찬, 분위기: 따뜻한, 키워드: 청년, 지원, 혜택"
                search_text = f"톤앤매너: {data.get('tone_and_manner', '')}, " \
                              f"분위기: {data.get('visual_vibe', '')}, " \
                              f"키워드: {', '.join(data.get('keywords', []))}"
                
                indexed_data.append(data) # 원본 데이터 보관
                texts_to_embed.append(search_text) # 임베딩할 텍스트 보관
            except: pass

    print(f"- 총 {len(indexed_data)}개의 데이터를 읽었습니다.")
    print("- AI가 이해할 수 있는 '벡터(숫자)'로 변환 중... (잠시 걸립니다)")

    # 2. AI 임베딩 생성 (배치 처리로 속도 업!)
    embeddings = []
    batch_size = 100
    for i in tqdm(range(0, len(texts_to_embed), batch_size), desc="임베딩 생성 중"):
        batch_texts = texts_to_embed[i:i+batch_size]
        try:
            # 구글 API로 텍스트를 벡터로 변환
            result = genai.embed_content(
                model=embedding_model,
                content=batch_texts,
                task_type="retrieval_document"
            )
            embeddings.extend(result['embedding'])
        except Exception as e:
            print(f"\n❌ 임베딩 오류 발생: {e}")
            # 오류 발생 시 해당 배치는 건너뛰거나 재시도 로직 필요 (간단히 넘김)
            embeddings.extend([None] * len(batch_texts))

    # 3. 최종 색인 데이터 저장 (원본 데이터 + 벡터 데이터)
    final_index = []
    success_count = 0
    for data, embedding in zip(indexed_data, embeddings):
        if embedding is not None:
            final_index.append({"data": data, "embedding": np.array(embedding)})
            success_count += 1
            
    with open(INDEX_FILE, 'wb') as f:
        pickle.dump(final_index, f)

    print(f"\n✨ 색인 생성 완료! (총 {success_count}개 저장됨)")
    print(f"결과 파일: {INDEX_FILE}")
    print("이제 스마트한 검색이 가능해졌습니다!")

if __name__ == "__main__":
    # numpy 설치 필요 (없으면 pip install numpy)
    try: import numpy; except ImportError: os.system("pip install numpy")
    create_index()
💻 2단계: [실행] RAG 기반 기획안 작성 (test_planner_rag.py)
이제 진짜입니다. 공고문 파일을 읽어서, 방금 만든 색인에서 가장 비슷한 예시 3개를 찾아온 다음, 그걸 참고해서 기획안을 짜는 코드입니다.

실행 방법:

sample_notice.txt (공고문 원문)이 같은 폴더에 있어야 합니다.

아래 코드를 test_planner_rag.py로 저장하세요.

API 키를 넣고 터미널에서 python test_planner_rag.py를 실행하세요.

Python

import os
import json
import pickle
import google.generativeai as genai
from pathlib import Path
import numpy as np

# ==========================================
# ⭐⭐⭐ API 키를 여기에 입력하세요 ⭐⭐⭐
GOOGLE_API_KEY = "YOUR_API_KEY_HERE"
# ==========================================

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
NOTICE_FILE = BASE_DIR / "sample_notice.txt"
INDEX_FILE = BASE_DIR / "gwangyang_style_index.pkl"

# 모델 설정
genai.configure(api_key=GOOGLE_API_KEY)
embedding_model = 'models/text-embedding-040' # 검색용 저렴한 모델
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

def run_rag_planner():
    print("🚀 [RAG 기반] 스마트 AI 기획자를 실행합니다...")

    # 1. 공고문 읽기
    if not NOTICE_FILE.exists():
        print("❌ 공고문 파일(sample_notice.txt)이 없습니다.")
        return
    with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
        source_text = f.read()
    print(f"📄 원문 읽기 완료 (길이: {len(source_text)}자)")

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
        print("👉 이 기획안은 '검색된 최적의 예시'를 기반으로 작성되어 품질이 높고 비용은 저렴합니다.")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        # print(f"응답 원문: {response.text}")

if __name__ == "__main__":
    # numpy 설치 필요
    try: import numpy; except ImportError: os.system("pip install numpy")
    run_rag_planner()
자, 이제 1번 코드를 한 번 실행해서 색인을 만들고, 2번 코드를 실행해서 결과를 확인해 보세요.

AI가 "유사도"를 계산해서 가장 비슷한 예시를 찾아내는 로그를 보시면, "아, 이래서 스마트하다고 하는구나!" 하고 바로 느끼실 겁니다. 비용 걱정 없는 고품질 기획의 시작입니다!