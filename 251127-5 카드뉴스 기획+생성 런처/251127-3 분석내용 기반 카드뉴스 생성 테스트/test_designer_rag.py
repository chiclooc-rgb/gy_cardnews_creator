import os
import json
import pickle
import google.generativeai as genai
from pathlib import Path
import numpy as np
import tkinter as tk
from tkinter import filedialog, simpledialog
from PIL import Image
import io
import datetime
import re
import time # 시간 지연을 위해 추가
import random # ### ⭐⭐⭐ [수정된 부분] 랜덤 라이브러리 추가 ⭐⭐⭐

# ==========================================
# ⭐⭐⭐ API 키를 여기에 입력하세요 ⭐⭐⭐
GOOGLE_API_KEY = "AIzaSyAIz1XZQdjLmLCqyrK8A_bmvoGi3RxjAP8"
# ==========================================

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "gwangyang_style_index.pkl"
OUTPUT_DIR = BASE_DIR / "완성된 카드뉴스"
OUTPUT_DIR.mkdir(exist_ok=True)

# 모델 설정
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    embedding_model = 'models/text-embedding-004' # 검색용
    # ⭐⭐⭐ 이미지 생성용 최신 모델 (Nano Banana Pro) ⭐⭐⭐
    designer_model = genai.GenerativeModel('gemini-3-pro-image-preview')
except Exception as e:
    print(f"❌ API 설정 중 오류 발생: {e}")
    exit()

def load_index():
    """색인 파일을 불러옵니다."""
    if not INDEX_FILE.exists():
        print(f"❌ 오류: 색인 파일을 찾을 수 없습니다 ({INDEX_FILE})")
        print("  ㄴ build_index.py를 먼저 실행하여 색인을 생성해주세요.")
        exit()
    with open(INDEX_FILE, 'rb') as f:
        return pickle.load(f)

# ⭐⭐⭐ [핵심 수정 함수] 다양성을 위해 랜덤 선택 로직 추가 ⭐⭐⭐
def find_best_reference_images(index, query_text, page_type, final_k=2):
    """입력 텍스트와 비슷한 스타일 후보군을 찾고, 그 중에서 랜덤으로 final_k개를 선택합니다."""
    try:
        # 1. 쿼리 임베딩
        print(f"  (잠시만 기다려주세요, '{page_type}' 스타일을 검색하고 있습니다...)")
        query_embedding = genai.embed_content(
            model=embedding_model, content=query_text, task_type="retrieval_query"
        )['embedding']
        query_vec = np.array(query_embedding)

        # 2. 전체 유사도 계산
        scores = []
        valid_indices = [] # 같은 페이지 타입인 인덱스만 저장
        for i, entry in enumerate(index):
            if entry['data'].get('page_type') == page_type:
                similarity = np.dot(query_vec, entry['embedding']) / (np.linalg.norm(query_vec) * np.linalg.norm(entry['embedding']))
                scores.append(similarity)
                valid_indices.append(i)
            else:
                scores.append(-1)
        
        if not valid_indices:
            return []

        # 3. [수정됨] 후보군(Pool) 뽑기
        # 상위 1등만 뽑는게 아니라, 상위 10개 정도(pool_size)를 후보로 둡니다.
        # 만약 전체 데이터가 10개보다 적으면 있는 만큼만 후보로 둡니다.
        pool_size = min(len(valid_indices), 15) 
        top_indices_pool = np.argsort(scores)[-pool_size:][::-1]
        
        # 4. [수정됨] 후보군 중에서 랜덤으로 final_k개 선택
        # final_k(기본2개) 보다 후보가 적으면 후보 전체를 선택
        num_to_select = min(len(top_indices_pool), final_k)
        selected_indices = random.sample(list(top_indices_pool), num_to_select)

        best_images = []
        print(f"\n🔍 ['{page_type}' 스타일] 검색 결과 (상위 {pool_size}개 중 랜덤 {num_to_select}개 선택):")
        
        for i in selected_indices:
            if scores[i] == -1: continue
            data = index[i]['data']
            img_path = Path(data.get('file_path'))
            if img_path.exists():
                # 점수 출력 대신 선택되었다는 표시만 함
                print(f"- [선택됨] 유사도 {scores[i]:.4f}: {img_path.name} (톤: {data.get('tone_and_manner')})")
                try:
                    img = Image.open(img_path)
                    best_images.append(img)
                except: print(f"  ㄴ ⚠️ 이미지 로드 실패: {img_path}")
        return best_images
    except Exception as e:
        print(f"❌ 스타일 검색 중 오류 발생: {e}")
        return []
# ⭐⭐⭐ 여기까지 수정됨 ⭐⭐⭐

def get_user_aspect_ratio():
    """사용자에게 이미지 비율을 선택받습니다."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    choices = ["4:5 (피드 권장)", "1:1 (정방형 피드)", "9:16 (릴스/스토리)"]
    choice = simpledialog.askstring(
        "비율 선택", 
        "생성할 카드뉴스의 비율을 선택하세요:\n" + "\n".join([f"{i+1}. {c}" for i, c in enumerate(choices)]) + "\n\n번호(1, 2, 3)를 입력하세요:",
        parent=root
    )
    root.destroy()
    
    if choice == '1': return "4:5"
    elif choice == '2': return "1:1"
    elif choice == '3': return "9:16"
    else: return None

# ⭐⭐⭐ [핵심 수정] 재시도 로직이 추가된 이미지 생성 함수 ⭐⭐⭐
def generate_image_with_retry(prompt_parts, output_path, aspect_ratio):
    """Nano Banana Pro 모델로 이미지를 생성하며, 500 에러 시 재시도 옵션을 제공합니다."""
    
    while True: # 성공하거나 사용자가 중단할 때까지 반복
        try:
            print(f"  ㄴ 🎨 AI 디자이너가 이미지를 그리는 중... (비율: {aspect_ratio}, Pro 모델)", flush=True)
            
            # 비율 설정 (프롬프트 방식 적용)
            prompt_parts_with_ratio = prompt_parts + [f"\n**[중요 기술 지시사항]** 최종 결과물의 이미지 비율은 반드시 **'{aspect_ratio}'**여야 합니다."]
            
            print("  (이미지 생성 요청을 보냈습니다. 응답을 기다리는 중... 최대 60초 소요)", flush=True)
            response = designer_model.generate_content(prompt_parts_with_ratio)
            
            generated_image = None
            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        image_data = part.inline_data.data
                        generated_image = Image.open(io.BytesIO(image_data))
                        break
            
            if generated_image:
                generated_image.save(output_path)
                print(f"  ㄴ ✅ 이미지 생성 및 저장 완료: {output_path.name}", flush=True)
                return True # 성공 시 함수 종료
            else:
                # 이미지가 안 왔지만 500 에러가 아닌 경우 (드묾)
                print("  ㄴ ⚠️ 생성 실패: API가 이미지를 반환하지 않았습니다.", flush=True)
                if response.text:
                    print(f"    응답 내용: {response.text}", flush=True)
                
                # 재시도 여부 묻기
                while True:
                    choice = input("🤔 이미지가 생성되지 않았습니다. 다시 시도할까요? (r: 다시 시도 / s: 건너뛰기): ").strip().lower()
                    if choice == 'r':
                        print("\n🔄 다시 시도합니다...", flush=True)
                        break # while True 루프 탈출 -> 외부 while 루프 반복 (재시도)
                    elif choice == 's':
                        print("⏭️ 이 페이지를 건너뜁니다.", flush=True)
                        return False # 실패로 종료
                    else:
                        print("r 또는 s를 입력해주세요.")

        except KeyboardInterrupt:
            print("\n\n🛑 사용자에 의해 중단되었습니다 (Ctrl+C).", flush=True)
            while True:
                choice = input("🤔 어떻게 할까요? (r: 다시 시도 / s: 이 페이지 건너뛰기 / q: 전체 종료): ").strip().lower()
                if choice == 'r': 
                    print("🔄 다시 시도합니다...", flush=True)
                    break # while True 루프의 처음으로 돌아감
                elif choice == 's': 
                    print("⏭️ 이 페이지를 건너뜁니다.", flush=True)
                    return False
                elif choice == 'q': 
                    print("👋 프로그램을 종료합니다.", flush=True)
                    exit()

        except Exception as e:
            error_msg = str(e)
            # 500 에러 또는 내부 서버 오류인 경우
            if "500" in error_msg or "internal error" in error_msg.lower():
                print("\n" + "="*40)
                print("🚨 구글 서버에 일시적인 문제가 발생했습니다 (500 Error).")
                print("   (서버가 바쁘거나 순간적인 오류일 수 있습니다.)")
                print("="*40)
                
                while True:
                    choice = input("🤔 어떻게 할까요? (r: 다시 시도 / s: 중단): ").strip().lower()
                    if choice == 'r':
                        print("\n🔄 서버에 휴식을 주고 3초 후 다시 시도합니다...", flush=True)
                        time.sleep(3) # 3초 대기 후 재시도
                        break # 내부 입력 루프 탈출 -> 외부 while 루프 반복
                    elif choice == 's':
                        print("🛑 생성을 중단합니다.", flush=True)
                        return False # 실패로 함수 종료
            else:
                # 500 에러가 아닌 다른 치명적 오류
                print(f"  ㄴ ❌ 알 수 없는 오류 발생: {e}", flush=True)
                return False # 실패로 함수 종료

def run_rag_designer():
    print("🚀 [RAG 기반] 스마트 AI 디자이너를 실행합니다...")

    # 0. 비율 선택
    aspect_ratio = get_user_aspect_ratio()
    if not aspect_ratio:
        print("❌ 비율이 선택되지 않아 취소되었습니다.")
        return
    print(f"✅ 선택된 비율: {aspect_ratio}")

    # 1. 기획안(JSON) 파일 선택
    print("📂 디자인할 기획안 파일(.json)을 선택해주세요...")
    try:
        root = tk.Tk()
        root.withdraw() # 메인 윈도우 숨김
        root.attributes('-topmost', True) # 창을 맨 위로
        json_path = filedialog.askopenfilename(
            title="기획안 파일(.json) 선택", 
            filetypes=[("JSON files", "*.json")], 
            initialdir=BASE_DIR
        )
        
        root.destroy()
    except Exception as e:
        print(f"❌ 파일 선택 창 오류: {e}")
        return

    if not json_path: 
        print("❌ 기획안이 선택되지 않아 취소되었습니다.")
        return
    
    # 1.5 캐릭터 이미지 자동 로드 (매돌이)
    character_dir = BASE_DIR / "매돌이 이미지"
    character_image = None
    
    if character_dir.exists():
        # 폴더 내의 첫 번째 이미지 파일을 찾습니다.
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.webp']
        for ext in image_extensions:
            try:
                found_images = list(character_dir.glob(ext))
                if found_images:
                    character_path = found_images[0]
                    character_image = Image.open(character_path)
                    print(f"✅ '매돌이' 캐릭터 이미지를 찾았습니다: {character_path.name}")
                    break
            except Exception as e:
                print(f"⚠️ 이미지 로드 중 오류: {e}")
        
        if not character_image:
            print(f"ℹ️ '{character_dir.name}' 폴더에 이미지 파일이 없습니다. 캐릭터 없이 진행합니다.")
    else:
        print(f"ℹ️ '{character_dir.name}' 폴더가 없습니다. 캐릭터 없이 진행합니다.")

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)
        print(f"📄 기획안 읽기 완료: {Path(json_path).name}")
    except Exception as e:
        print(f"❌ 기획안 파일 읽기 오류: {e}")
        return

    # 2. 색인 로드 및 스타일 정의
    print("📚 스타일 색인을 불러오는 중...")
    index = load_index()
    tone = plan_data.get("estimated_tone", "광양시 스타일")
    print(f"🎨 목표 스타일: '{tone}'")
    
    # 3. 페이지별 이미지 생성 시작
    plan = plan_data.get("plan", {})
    if not plan:
        print("❌ 기획안에 'plan' 데이터가 없습니다.")
        return

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

    # 시작 페이지 선택
    while True:
        try:
            start_page_input = input(f"몇 번째 페이지부터 생성하시겠습니까? (1~{total_pages}, 엔터 치면 1번부터): ").strip()
            if not start_page_input:
                start_page_idx = 0
                break
            start_page_idx = int(start_page_input) - 1
            if 0 <= start_page_idx < total_pages:
                break
            else:
                print(f"1부터 {total_pages} 사이의 숫자를 입력해주세요.")
        except ValueError:
            print("숫자를 입력해주세요.")
    
    base_filename = Path(json_path).stem.split(' ', 1)[-1] # 날짜 제외한 파일명
    # 파일명에 사용할 수 없는 문자 제거
    safe_base_filename = re.sub(r'[\\/*?:"<>|]', "", base_filename)

    generate_all = False # '나머지 모두 생성' 모드 플래그

    # ⭐⭐⭐ [핵심 수정] 페이지 타입별로 레퍼런스를 미리 검색 (본문 일관성 확보) ⭐⭐⭐
    print("\n🔍 페이지 타입별 레퍼런스 이미지를 미리 검색합니다...")
    ref_images_cache = {}
    
    # 각 페이지 타입별로 한 번씩만 레퍼런스 검색
    page_types_needed = set(page['type'] for page in pages_to_generate)
    for page_type in page_types_needed:
        query_text = f"{tone} 느낌의 {page_type} 디자인 스타일"
        ref_images_cache[page_type] = find_best_reference_images(index, query_text, page_type, final_k=2)
        if not ref_images_cache[page_type]:
            print(f"⚠️ '{page_type}' 타입의 레퍼런스를 찾지 못했습니다. 기본 스타일로 진행합니다.")
    
    print("\n✅ 레퍼런스 검색 완료! 이제 이미지를 생성합니다.\n")

    for i, page in enumerate(pages_to_generate):
        if i < start_page_idx:
            continue

        print(f"\n[{i+1}/{total_pages}] '{page['type']}' 페이지 생성 시작...")
        
        # 미리 검색한 레퍼런스 사용 (본문은 모두 동일한 레퍼런스 사용)
        ref_images = ref_images_cache.get(page['type'], [])
        
        if not ref_images:
            print("⚠️ 적절한 레퍼런스 이미지를 찾지 못했습니다. 기본 스타일로 진행합니다.")
        
        # 프롬프트 구성
        content_text = json.dumps(page['data'], ensure_ascii=False, indent=2)
        # ⭐⭐⭐ [핵심 수정] 프롬프트 대폭 강화 ⭐⭐⭐
        prompt_parts = [
            "당신은 광양시청의 전문 카드뉴스 디자이너입니다.",
            f"제공된 참조 이미지들의 **'{tone}' 스타일과 레이아웃**을 완벽하게 반영하여, 아래 텍스트 내용을 담은 새로운 카드뉴스 이미지를 만들어주세요.",
            f"페이지 타입: {page['type']}",
            "**[필수 지시사항]**",
            "1. 텍스트는 반드시 **한글이 깨지지 않게 디자인과 완벽하게 어우러지도록** 크고 명확하게 배치해야 합니다.",
            "2. 모든 페이지는 일관된 톤앤매너를 유지해야 합니다.",
        ]
        
        # ⭐⭐⭐ [핵심 수정] 매돌이 사용 여부를 조건부로 변경 ⭐⭐⭐
        if character_image:
            prompt_parts.append("\n**[매돌이 캐릭터 활용 지시사항 (조건부)]**")
            prompt_parts.append("제공된 매돌이 캐릭터 이미지의 사용 여부는 전적으로 **참조 이미지(레퍼런스)의 스타일**에 따라 판단하세요.")
            prompt_parts.append("1. **분석:** 먼저 함께 제공된 참조 이미지들이 캐릭터를 디자인 요소로 사용하고 있는지 시각적으로 분석하세요.")
            prompt_parts.append("2. **적용 (캐릭터 스타일인 경우):** 만약 참조 이미지들에 캐릭터가 포함되어 있다면, 제공된 '매돌이' 이미지를 해당 위치나 스타일에 맞춰 자연스럽게 배치하세요.")
            prompt_parts.append("3. **미적용 (비캐릭터 스타일인 경우):** 만약 참조 이미지들이 텍스트와 그래픽 위주이고 캐릭터가 없다면, 이 디자인에도 캐릭터를 넣지 마세요.")
            prompt_parts.append("4. **고유성 유지 (매우 중요):** 캐릭터를 넣기로 결정했다면, 제공된 '매돌이' 이미지의 외형(생김새, 색상)을 절대 변형하지 말고 그대로 사용해야 합니다. (새로 그리기 금지)")
            prompt_parts.append(character_image) # 이미지는 일단 제공하여 판단하게 함
        else:
             prompt_parts.append("\n**[캐릭터 관련 지시사항]**")
             prompt_parts.append("이 디자인에는 어떠한 인물이나 캐릭터도 등장시키지 마세요.")

        prompt_parts.extend([
            "\n[들어갈 텍스트 내용]",
            content_text,
            *ref_images
        ])
        # ⭐⭐⭐ 여기까지 ⭐⭐⭐
        
        # 이미지 생성 및 저장
        output_filename = f"{safe_base_filename}_{page['filename_suffix']}.png"
        output_path = OUTPUT_DIR / output_filename
        
        # 파일명 중복 처리
        counter = 1
        while output_path.exists():
            output_filename = f"{safe_base_filename}_{page['filename_suffix']}_{counter}.png"
            output_path = OUTPUT_DIR / output_filename
            counter += 1
        
        if generate_image_with_retry(prompt_parts, output_path, aspect_ratio):
            if i == 0:
                print(f"\n👀 첫 번째 장({output_filename})이 생성되었습니다. 확인해보세요!")
                try: os.startfile(output_path)
                except: pass
                
                while True:
                    check = input("\n🤔 결과가 마음에 드시나요? 나머지 페이지도 계속 생성할까요? (y/n): ").strip().lower()
                    if check == 'y':
                        print("🚀 나머지 페이지 생성을 진행합니다...")
                        break
                    elif check == 'n':
                        print("🛑 작업을 중단합니다.")
                        return
                    else:
                        print("y 또는 n을 입력해주세요.")
            else:
                # 첫 장이 아닐 경우, 연속 호출로 인한 서버 과부하/차단을 막기 위해 대기 시간 추가
                if i < total_pages - 1: # 마지막 장이 아닐 때만
                    print("\n☕ 구글 서버 과부하 방지를 위해 10초간 휴식합니다... (Rate Limit 예방)")
                    time.sleep(10)
        else:
             # 생성 실패(중단 선택) 시 전체 작업 중단
             print("\n❌ 이미지 생성에 실패하여 전체 작업을 중단합니다.")
             return

if __name__ == "__main__":
    # numpy, pillow, tkinter 필요
    try: 
        import numpy, PIL, tkinter
    except ImportError: 
        print("필요한 라이브러리를 설치합니다...")
        os.system("pip install numpy pillow")
        # tkinter는 보통 python 기본 포함이지만, 없으면 별도 설치 필요할 수 있음
    
    run_rag_designer()
