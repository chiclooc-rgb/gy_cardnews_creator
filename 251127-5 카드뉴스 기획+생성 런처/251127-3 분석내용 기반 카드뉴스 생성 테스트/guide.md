아하, 아까 에러는 가상 환경 문제였군요\! 해결됐다니 다행입니다. 😅

자, 그럼 이제 본격적인 **"AI 디자이너(Nano Banana Pro)"의 차례**입니다\! 방금 만든 기획안(JSON)을 가지고, 스타일 색인(Index)에서 가장 비슷한 레퍼런스를 찾아와서, 최종 카드뉴스 이미지를 생성하는 코드를 만들어 보겠습니다.

사용자 님께서 주신 `run_mvp_test.py` 코드를 바탕으로, RAG(검색) 기능과 다중 이미지 생성 기능을 추가하여 완성형 코드로 만들었습니다.

-----

### 🎨 최종 AI 디자이너 코드 (`test_designer_rag.py`)

이 코드는 아까 만든 **기획안 JSON 파일을 선택**하면, 알아서 스타일을 검색하고 최종 이미지를 생성합니다.

**실행 방법:**

1.  아래 코드를 `test_designer_rag.py`로 저장하세요. (`build_index.py`, `test_planner_rag.py`와 같은 폴더)
2.  API 키를 넣고 터미널에서 `python test_designer_rag.py`를 실행하세요.
3.  파일 선택 창이 뜨면, 아까 `test_planner_rag.py`로 만든 **기획안 JSON 파일** (예: `2025-11-27 ... .json`)을 선택하세요.

<!-- end list -->

```python
import os
import json
import pickle
import google.generativeai as genai
from pathlib import Path
import numpy as np
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import io
import datetime
import re

# ==========================================
# ⭐⭐⭐ API 키를 여기에 입력하세요 ⭐⭐⭐
GOOGLE_API_KEY = "YOUR_API_KEY_HERE"
# ==========================================

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "gwangyang_style_index.pkl"
OUTPUT_DIR = BASE_DIR / "완성된 카드뉴스"
OUTPUT_DIR.mkdir(exist_ok=True)

# 모델 설정
genai.configure(api_key=GOOGLE_API_KEY)
embedding_model = 'models/text-embedding-004' # 검색용
# ⭐⭐⭐ 이미지 생성용 최신 모델 (Nano Banana Pro) ⭐⭐⭐
designer_model = genai.GenerativeModel('gemini-3-pro-image-preview')

def load_index():
    """색인 파일을 불러옵니다."""
    if not INDEX_FILE.exists():
        print(f"❌ 오류: 색인 파일을 찾을 수 없습니다 ({INDEX_FILE})")
        exit()
    with open(INDEX_FILE, 'rb') as f:
        return pickle.load(f)

def find_best_reference_images(index, query_text, page_type, top_k=3):
    """입력 텍스트와 가장 비슷한 스타일의 레퍼런스 이미지를 검색합니다."""
    query_embedding = genai.embed_content(
        model=embedding_model, content=query_text, task_type="retrieval_query"
    )['embedding']
    query_vec = np.array(query_embedding)

    scores = []
    for entry in index:
        # 같은 페이지 타입(표지, 본문 등) 중에서만 검색
        if entry['data'].get('page_type') == page_type:
            similarity = np.dot(query_vec, entry['embedding']) / (np.linalg.norm(query_vec) * np.linalg.norm(entry['embedding']))
            scores.append(similarity)
        else:
            scores.append(-1) # 다른 타입은 제외
    
    top_indices = np.argsort(scores)[-top_k:][::-1]
    best_images = []
    print(f"\n🔍 ['{page_type}' 스타일] 검색 결과 (Top {top_k}):")
    for i in top_indices:
        if scores[i] == -1: continue # 유효한 결과가 없을 경우 건너뜀
        data = index[i]['data']
        img_path = Path(data.get('file_path'))
        if img_path.exists():
            print(f"- 유사도 {scores[i]:.4f}: {img_path.name} (톤: {data.get('tone_and_manner')})")
            try:
                img = Image.open(img_path)
                best_images.append(img)
            except: print(f"  ㄴ ⚠️ 이미지 로드 실패: {img_path}")
    return best_images

def generate_image(prompt_parts, output_path):
    """Nano Banana Pro 모델로 이미지를 생성하고 저장합니다."""
    try:
        print("  ㄴ 🎨 AI 디자이너가 이미지를 그리는 중... (Pro 모델이라 조금 걸립니다)")
        response = designer_model.generate_content(prompt_parts)
        
        generated_image = None
        if response.parts:
            for part in response.parts:
                if part.inline_data:
                    image_data = part.inline_data.data
                    generated_image = Image.open(io.BytesIO(image_data))
                    break
        
        if generated_image:
            generated_image.save(output_path)
            print(f"  ㄴ ✅ 이미지 생성 및 저장 완료: {output_path.name}")
            return True
        else:
            print("  ㄴ ⚠️ 생성 실패: API가 이미지를 반환하지 않았습니다.")
            return False
    except Exception as e:
        print(f"  ㄴ ❌ 오류 발생: {e}")
        return False

def run_rag_designer():
    print("🚀 [RAG 기반] 스마트 AI 디자이너를 실행합니다...")

    # 1. 기획안(JSON) 파일 선택
    print("📂 디자인할 기획안 파일(.json)을 선택해주세요...")
    root = tk.Tk()
    root.withdraw()
    json_path = filedialog.askopenfilename(
        title="기획안 파일(.json) 선택", filetypes=[("JSON files", "*.json")], initialdir=BASE_DIR / "카드뉴스 문안"
    )
    if not json_path: print("❌ 취소되었습니다."); return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        plan_data = json.load(f)
    print(f"📄 기획안 읽기 완료: {Path(json_path).name}")

    # 2. 색인 로드 및 스타일 정의
    print("📚 스타일 색인을 불러오는 중...")
    index = load_index()
    tone = plan_data.get("estimated_tone", "광양시 스타일")
    print(f"🎨 목표 스타일: '{tone}'")
    
    # 3. 페이지별 이미지 생성 시작
    plan = plan_data["plan"]
    pages_to_generate = []
    
    # 3-1. 표지 (COVER)
    if "cover" in plan:
        pages_to_generate.append({
            "type": "COVER",
            "data": plan["cover"],
            "filename_suffix": "00_cover"
        })
    
    # 3-2. 본문 (BODY) - 여러 장일 수 있음
    if "body" in plan:
        for i, page in enumerate(plan["body"]):
            pages_to_generate.append({
                "type": "BODY",
                "data": page,
                "filename_suffix": f"{i+1:02d}_body"
            })
            
    # 3-3. 마무리 (OUTRO)
    if "outro" in plan:
        pages_to_generate.append({
            "type": "OUTRO",
            "data": plan["outro"],
            "filename_suffix": "99_outro"
        })

    # 4. 순차적으로 생성 실행
    total_pages = len(pages_to_generate)
    print(f"\n총 {total_pages}장의 카드뉴스 이미지를 생성합니다.")
    
    base_filename = Path(json_path).stem.split(' ', 1)[-1] # 날짜 제외한 파일명
    safe_base_filename = re.sub(r'[\\/*?:"<>|]', "", base_filename)

    for i, page in enumerate(pages_to_generate):
        print(f"\n[{i+1}/{total_pages}] '{page['type']}' 페이지 생성 시작...")
        
        # 스타일 레퍼런스 검색
        query_text = f"{tone} 느낌의 {page['type']} 디자인 스타일"
        ref_images = find_best_reference_images(index, query_text, page['type'], top_k=2)
        
        if not ref_images:
            print("⚠️ 적절한 레퍼런스 이미지를 찾지 못했습니다. 기본 스타일로 진행합니다.")
        
        # 프롬프트 구성
        content_text = json.dumps(page['data'], ensure_ascii=False, indent=2)
        prompt_parts = [
            "당신은 광양시청의 전문 카드뉴스 디자이너입니다.",
            f"제공된 참조 이미지들의 **'{tone}' 스타일과 디자인 레이아웃**을 완벽하게 반영하여, 아래 텍스트 내용을 담은 새로운 카드뉴스 이미지를 만들어주세요.",
            f"페이지 타입: {page['type']}",
            "**필수 지시사항:** 텍스트는 반드시 **한글이 깨지지 않게 디자인과 완벽하게 어우러지도록** 크고 명확하게 배치해야 합니다.",
            "\n[들어갈 텍스트 내용]",
            content_text,
            *ref_images # 참조 이미지들 추가
        ]
        
        # 이미지 생성 및 저장
        output_filename = f"{safe_base_filename}_{page['filename_suffix']}.png"
        output_path = OUTPUT_DIR / output_filename
        generate_image(prompt_parts, output_path)

    print("\n" + "="*60)
    print(f"🎉 모든 작업이 완료되었습니다! 결과 폴더를 확인하세요: {OUTPUT_DIR}")
    print("="*60)
    try: os.startfile(OUTPUT_DIR)
    except: pass

if __name__ == "__main__":
    # numpy, pillow, tkinter 필요
    try: import numpy, PIL, tkinter; except ImportError: os.system("pip install numpy pillow tkinter")
    run_rag_designer()
```

-----

### ✨ 이 코드가 하는 일 (기적의 과정)

1.  **기획안 읽기:** 아까 AI 기획자가 만든 JSON 파일을 읽습니다. (예: "표지 제목: 광양시 청년 면접 정장 대여\!")
2.  **스타일 검색 (RAG):** 색인(Index)을 뒤져서 "표지이면서 활기찬 느낌"인 과거 레퍼런스 이미지 2장을 찾아옵니다.
3.  **AI 디자이너 호출:** 기획안 텍스트와 찾아온 레퍼런스 이미지를 묶어서 Nano Banana Pro에게 보냅니다. "이 스타일로 이 내용을 그려줘\!"
4.  **최종 생성:** 표지, 본문1, 본문2... 순서대로 이미지를 쭉쭉 뽑아내고 `완성된 카드뉴스` 폴더에 저장합니다.

자, 이제 이 코드를 돌리면 **글자뿐이던 기획안이 진짜 카드뉴스 이미지로 변신하는 마법**을 보시게 될 겁니다. 실행해 보세요\! 😄