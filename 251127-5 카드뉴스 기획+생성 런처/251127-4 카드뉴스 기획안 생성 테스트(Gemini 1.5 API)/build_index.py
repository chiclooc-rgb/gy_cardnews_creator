import os
import json
import pickle
import google.generativeai as genai
from pathlib import Path
from tqdm import tqdm
import numpy as np

# ==========================================
# ⭐⭐⭐ API 키를 여기에 입력하세요 ⭐⭐⭐
GOOGLE_API_KEY = "AIzaSyB3i6xfiLGp3293-Rx5cj2Vee5A0slcASM"
# ==========================================

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "gwangyang_style_db.jsonl"
INDEX_FILE = BASE_DIR / "gwangyang_style_index.pkl"

# 임베딩 모델 설정 (텍스트를 벡터 숫자로 바꿔주는 저렴한 모델)
genai.configure(api_key=GOOGLE_API_KEY)
embedding_model = 'models/text-embedding-004'

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
    try:
        import numpy
    except ImportError:
        os.system("pip install numpy")
        import numpy
        
    create_index()
