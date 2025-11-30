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
import time
import random
import sys
import io
from pypdf import PdfReader # PDF 텍스트 추출용 (검색 쿼리 생성 목적)

# Windows 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ==========================================
# ⭐⭐⭐ API 키를 여기에 입력하세요 ⭐⭐⭐
GOOGLE_API_KEY = "AIzaSyAIz1XZQdjLmLCqyrK8A_bmvoGi3RxjAP8"
# ==========================================

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "gwangyang_style_index.pkl"
OUTPUT_DIR = BASE_DIR / "카드뉴스 문안"
OUTPUT_DIR.mkdir(exist_ok=True)

# 모델 설정
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    embedding_model = 'models/text-embedding-004'
    # 기획 및 PDF 분석에 최적화된 모델
    planning_model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    print(f"❌ API 설정 오류: {e}")
    exit()

def load_index():
    if not INDEX_FILE.exists():
        print(f"❌ 오류: 색인 파일을 찾을 수 없습니다 ({INDEX_FILE})")
        print("  ㄴ build_index.py를 먼저 실행해주세요.")
        exit()
    with open(INDEX_FILE, 'rb') as f:
        return pickle.load(f)

# ⭐ [수정] 랜덤 다양성 로직 적용 ⭐
def find_best_examples(index, query_text, top_k=3):
    """입력 내용과 비슷한 스타일을 찾되, 후보군 내에서 랜덤 선택하여 다양성 확보"""
    try:
        query_embedding = genai.embed_content(
            model=embedding_model, content=query_text, task_type="retrieval_query"
        )['embedding']
        query_vec = np.array(query_embedding)

        scores = []
        for entry in index:
            similarity = np.dot(query_vec, entry['embedding']) / (np.linalg.norm(query_vec) * np.linalg.norm(entry['embedding']))
            scores.append(similarity)

        # 1. 상위 15개 후보군(Pool) 추출
        pool_size = min(len(scores), 15)
        top_indices_pool = np.argsort(scores)[-pool_size:][::-1]

        # 2. 후보군 내에서 랜덤 선택 (다양성)
        selected_indices = random.sample(list(top_indices_pool), min(pool_size, top_k))

        best_examples = []
        print(f"\n🔍 스타일 검색 결과 (상위 {pool_size}개 중 랜덤 {top_k}개):")
        for i in selected_indices:
            data = index[i]['data']
            # 유사도는 참고용으로 출력
            print(f"- [선택됨] {data.get('file_name')} (톤: {data.get('tone_and_manner')})")

            example_summary = {
                "type": data.get("page_type"),
                "title_style": data.get("main_title"),
                "body_summary_style": data.get("body_summary"),
                "tone": data.get("tone_and_manner")
            }
            best_examples.append(json.dumps(example_summary, ensure_ascii=False))

        return "\n".join(best_examples)
    except Exception as e:
        print(f"⚠️ 스타일 검색 중 오류: {e}")
        return ""

def select_input_file():
    """TXT 또는 PDF 파일 선택"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(
        title="분석할 공고문 파일(TXT, PDF)을 선택하세요",
        filetypes=[("Documents", "*.txt;*.pdf"), ("Text files", "*.txt"), ("PDF files", "*.pdf")],
        initialdir=BASE_DIR
    )
    root.destroy()
    if file_path: return Path(file_path)
    return None

def process_input_file(file_path, max_retries=3):
    """파일 확장자에 따라 처리 방식 분기 (재시도 로직 포함)"""
    ext = file_path.suffix.lower()

    # 1. TXT 파일 처리
    if ext == '.txt':
        print("📄 텍스트 파일 감지됨.")
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return {
            "type": "text",
            "content": text,  # 프롬프트에 직접 넣을 텍스트
            "query": text[:500] # 검색용 쿼리
        }

    # 2. PDF 파일 처리 (재시도 로직 포함)
    elif ext == '.pdf':
        print("📑 PDF 파일 감지됨.")

        # 검색용 텍스트 추출 (pypdf 사용)
        try:
            reader = PdfReader(file_path)
            query_text = ""
            # 앞쪽 2페이지 정도만 읽어서 검색 쿼리로 사용
            for i in range(min(2, len(reader.pages))):
                query_text += reader.pages[i].extract_text()
            if not query_text: query_text = "공고문"
        except Exception as e:
            print(f"⚠️ PDF 텍스트 추출 실패: {e}")
            query_text = "공고문"

        # 분석용 파일 업로드 (Gemini API - AI가 직접 파일을 읽음)
        # 재시도 로직 추가
        uploaded_file = None
        for attempt in range(max_retries):
            try:
                print(f"☁️ 표/서식 분석을 위해 PDF를 구글 서버로 전송 중... (시도 {attempt + 1}/{max_retries})")
                uploaded_file = genai.upload_file(path=file_path, display_name="Notice PDF")
                break
            except Exception as e:
                print(f"⚠️ 업로드 실패 (시도 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 지수 백오프: 1초, 2초, 4초
                    print(f"   {wait_time}초 후 재시도합니다...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"PDF 업로드 실패 (최대 {max_retries}회 시도)")

        # 파일 상태 확인 및 대기 (재시도 로직 포함)
        print("   (잠시만 기다려주세요...)", end="")
        processing_timeout = 60  # 최대 60초 대기
        start_time = time.time()

        while uploaded_file.state.name == "PROCESSING":
            if time.time() - start_time > processing_timeout:
                raise Exception(f"PDF 처리 타임아웃 ({processing_timeout}초 초과)")

            print(".", end="", flush=True)
            time.sleep(2)

            try:
                uploaded_file = genai.get_file(uploaded_file.name)
            except Exception as e:
                print(f"\n⚠️ 파일 상태 조회 실패: {e}")
                time.sleep(2)
                continue

        if uploaded_file.state.name == "FAILED":
            raise Exception("PDF 처리 실패 - 파일이 손상되었거나 형식이 올바르지 않습니다.")

        print("\n✅ PDF 업로드 완료.")
        return {
            "type": "file",
            "content": uploaded_file,  # 프롬프트에 넣을 파일 객체
            "query": query_text[:500]
        }

    else:
        raise ValueError("지원하지 않는 파일 형식입니다. (TXT 또는 PDF만 가능)")

def run_planner():
    print("🚀 [통합형] AI 기획자를 실행합니다... (TXT/PDF + 랜덤 검색 지원)")

    # 1. 파일 선택
    print("📂 공고문 파일을 선택해주세요...")
    input_file = select_input_file()
    if not input_file: print("❌ 취소됨."); return

    try:
        # 2. 파일 처리 (TXT 읽기 or PDF 업로드 + 재시도)
        file_data = process_input_file(input_file)

        # 3. 스타일 검색 (RAG + 랜덤)
        print("📚 스타일 색인을 검색하는 중...")
        index = load_index()
        best_examples_context = find_best_examples(index, file_data["query"], top_k=3)

        # 4. 프롬프트 구성
        prompt_parts = [
            "당신은 광양시청 홍보팀의 수석 카드뉴스 기획자입니다.",
            "제공된 **공고문(텍스트 또는 PDF)**을 정밀하게 분석하세요. 특히 PDF의 경우 **표(Table)에 담긴 핵심 정보(대상, 금액, 기간 등)**를 누락 없이 파악해야 합니다.",
            "그 후, 아래 [검색된 유사 스타일 예시]를 참고하여 광양시 특유의 친근하고 명확한 톤앤매너로 기획안을 작성하세요.",
            "\n[검색된 유사 스타일 예시 (참고용)]",
            best_examples_context,
            "\n[분석할 공고문 원본]",
            file_data["content"],  # 텍스트 또는 PDF 파일 객체 들어감
            "\n[지시사항]",
            "1. **구조 판단:** 내용이 단순하면 `SINGLE(1장)`, 복잡하면 `MULTI(표지-본문-마무리)` 구조로 기획하세요.",
            "2. **내용 요약:** 공고문의 핵심 정보를 누락 없이, 카드뉴스에 적합한 짧고 명확한 문장으로 요약하세요.",
            "3. **출력 형식:** 반드시 아래 **순수한 JSON 형식**으로만 출력하세요. (마크다운 제외)",
            """
            {
              "structure_type": "MULTI",
              "plan": {
                "cover": { "main_title": "...", "sub_title": "..." },
                "body": [ { "page": 1, "summary": ["..."] }, ... ],
                "outro": { "contact": "..." }
              },
              "estimated_tone": "(예: 활기찬, 정보성)"
            }
            """
        ]

        print("\n🧠 AI가 기획안을 작성 중입니다...")

        # 5. API 호출 (재시도 로직)
        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = planning_model.generate_content(prompt_parts)
                break
            except Exception as e:
                print(f"⚠️ 기획안 생성 실패 (시도 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"   {wait_time}초 후 재시도합니다...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"기획안 생성 실패 (최대 {max_retries}회 시도)")

        response_text = response.text.strip()
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.endswith("```"): response_text = response_text[:-3]

        plan_data = json.loads(response_text)

        # 6. 결과 저장
        try:
            title = plan_data["plan"]["cover"]["main_title"]
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        except: safe_title = "제목없음"

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        filename = f"{today} {safe_title}.json"
        output_path = OUTPUT_DIR / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, indent=2, ensure_ascii=False)

        print("\n" + "="*60)
        print("🎉 [성공] 기획안이 완성되었습니다!")
        print(f"저장 위치: {output_path}")
        print("="*60)
        print(json.dumps(plan_data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

if __name__ == "__main__":
    # pypdf 설치 확인
    try: import pypdf
    except ImportError:
        print("pypdf 라이브러리를 설치합니다...")
        os.system("pip install pypdf")

    run_planner()
