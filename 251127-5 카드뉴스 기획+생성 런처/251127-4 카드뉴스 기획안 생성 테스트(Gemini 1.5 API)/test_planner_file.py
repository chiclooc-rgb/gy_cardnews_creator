import os
import json
import google.generativeai as genai
from pathlib import Path
import random

# ==========================================
# ⭐⭐⭐ API 키를 여기에 입력하세요 ⭐⭐⭐
GOOGLE_API_KEY = "AIzaSyAIz1XZQdjLmLCqyrK8A_bmvoGi3RxjAP8"
# ==========================================

# 경로 및 설정
BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "gwangyang_style_db.jsonl"
# ⭐⭐⭐ 테스트할 공고문 파일명 (스크립트와 같은 폴더에 위치) ⭐⭐⭐
NOTICE_FILE = BASE_DIR / "sample_notice.txt"

# 텍스트 전용 모델 사용 (기획 능력이 뛰어난 Pro 모델)
genai.configure(api_key=GOOGLE_API_KEY)
# Gemini 1.5 Pro 모델을 사용합니다. 모델명은 상황에 따라 변경될 수 있습니다.
model = genai.GenerativeModel('gemini-2.5-pro')

def load_style_examples(db_path, num_examples=5):
    """DB 파일에서 스타일 참고용 예시 데이터를 랜덤하게 뽑아옵니다."""
    examples = []
    if not db_path.exists():
        print(f"❌ 오류: DB 파일을 찾을 수 없습니다 ({db_path})")
        print("먼저 build_db.py를 실행해서 DB를 구축해주세요.")
        exit()
        
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 데이터가 너무 많으면 랜덤으로 일부만 샘플링
            sampled_lines = random.sample(lines, min(len(lines), 20)) 
            for line in sampled_lines:
                try:
                    data = json.loads(line)
                    # 필요한 필드만 골라서 예시로 사용
                    example = {
                        "type": data.get("page_type"),
                        "title_style": data.get("main_title"),
                        "sub_style": data.get("sub_title"),
                        "body_style": data.get("body_summary"),
                        "tone": data.get("tone_and_manner")
                    }
                    examples.append(json.dumps(example, ensure_ascii=False))
                except: pass
    except Exception as e:
        print(f"⚠️ DB 읽기 중 오류: {e}")
    
    # 최종적으로 몇 개만 추려서 반환
    return "\n".join(examples[:num_examples])

def run_planner_test_file():
    print("🚀 AI 기획자 모듈 (파일 기반) 테스트를 시작합니다...")

    # 0. 공고문 파일 읽기
    if not NOTICE_FILE.exists():
        print(f"❌ 오류: 공고문 파일을 찾을 수 없습니다 ({NOTICE_FILE})")
        print(f"테스트할 공고문 내용을 담은 '{NOTICE_FILE.name}' 파일을 준비해주세요.")
        return
    
    try:
        with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
            source_text = f.read()
        print(f"📄 공고문 파일을 성공적으로 읽었습니다. (파일명: {NOTICE_FILE.name}, 길이: {len(source_text)}자)")
    except Exception as e:
        print(f"❌ 파일 읽기 오류: {e}")
        return

    # 1. DB에서 스타일 참고자료 로드 (In-context Learning의 핵심!)
    print("📚 DB에서 광양시 스타일 예시를 학습하는 중...")
    style_context = load_style_examples(DB_FILE)
    
    if not style_context:
         print("⚠️ DB에서 유의미한 데이터를 찾지 못했습니다. 기본 스타일로 진행합니다.")
         style_context = "(참고할 데이터 없음)"

    # 2. 프롬프트 구성
    prompt = f"""
    당신은 광양시청 홍보팀의 베테랑 카드뉴스 기획자입니다.
    아래 제공된 '기존 광양시 카드뉴스 스타일 예시'를 분석하여 광양시 특유의 톤앤매너, 제목 뽑는 방식, 정보 요약 스타일을 완벽하게 파악하세요.

    그리고 그 스타일을 적용하여, 제공된 '원문 공고'를 바탕으로 4장 내외의 카드뉴스 기획안을 작성해주세요.

    [기존 광양시 카드뉴스 스타일 예시 (참고용)]
    {style_context}

    ---

    [원문 공고]
    {source_text}

    ---

    [지시사항]
    1. **구조:** 반드시 `COVER(1장)`, `BODY(여러 장)`, `OUTRO(1장)` 구조로 기획하세요.
    2. **톤앤매너:** 위 예시에서 파악한 광양시 스타일(친근함, 명확함, 혜택 강조 등)을 적용하세요.
    3. **출력 형식:** 반드시 아래와 같은 **순수한 JSON 형식**으로만 출력하세요. 마크다운(`json`) 코드는 넣지 마세요.

    [출력 예시 형식]
    {{
      "cover": {{ "main_title": "...", "sub_title": "..." }},
      "body": [
        {{ "page_num": 1, "title": "...", "content_summary": ["핵심1", "핵심2"] }},
        {{ "page_num": 2, "title": "...", "content_summary": ["핵심3", "핵심4"] }}
      ],
      "outro": {{ "main_text": "...", "contact_info": "..." }}
    }}
    """

    print("\n🧠 AI가 기획안을 작성 중입니다... (잠시만 기다려주세요)")
    
    try:
        # 3. API 호출
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # 마크다운 제거 (혹시 붙어 나올 경우)
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        
        # JSON 파싱 및 결과 출력
        plan_data = json.loads(response_text)
        
        print("\n" + "="*60)
        print("🎉 [테스트 성공] AI 기획안 생성 완료!")
        print("="*60)
        # 보기 좋게 출력
        print(json.dumps(plan_data, indent=2, ensure_ascii=False))
        print("="*60)

        # 4. JSON 파일로 저장
        OUTPUT_FILE = BASE_DIR / "planner_result.json"
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 기획안이 JSON 파일로 저장되었습니다: {OUTPUT_FILE}")
        print("👉 이 JSON 데이터가 다음 단계에서 디자인 생성의 기초 자료로 사용됩니다.")

    except Exception as e:
        print(f"\n❌ 기획안 생성 실패: {e}")
        if 'response_text' in locals():
             print(f"응답 원문: {response_text}")

if __name__ == "__main__":
    run_planner_test_file()