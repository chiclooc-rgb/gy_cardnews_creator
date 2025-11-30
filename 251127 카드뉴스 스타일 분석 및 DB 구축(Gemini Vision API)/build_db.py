import os
import glob
import json
import time
import typing
import google.generativeai as genai
from PIL import Image
from tqdm import tqdm

# Configuration
API_KEY = "AIzaSyAIz1XZQdjLmLCqyrK8A_bmvoGi3RxjAP8" # Fixed: Direct string assignment
MODEL_NAME = "gemini-2.5-flash"
OUTPUT_FILE = "gwangyang_cardnews_db.jsonl"
BASE_DIR = r"c:\Users\a\Desktop\작업파일(디자인, AI 등)\251127 카드뉴스 스타일 분석 및 DB 구축(Gemini Vision API)\sorted_output\img"
TEST_LIMIT = None # Process all images

# Directory Mapping
DIR_MAP = {
    "COVER": os.path.join(BASE_DIR, "10_gy_cover"),
    "BODY": os.path.join(BASE_DIR, "10_gy_body"),
    "OUTRO": os.path.join(BASE_DIR, "10_gy_outro"),
}

# Prompts
SYSTEM_PROMPT = """당신은 20년 경력의 베테랑 디자인&콘텐츠 분석가입니다. 제공된 카드뉴스 이미지를 심층 분석하여 기획 의도, 텍스트 구성, 디자인 스타일을 완벽하게 파악하고, 이를 기계가 이해할 수 있는 구조화된 데이터로 추출하는 임무를 맡았습니다."""

ANALYSIS_PROMPT = """
각 이미지와 함께 다음 질문을 전송하여 상세 정보를 추출한다.

1. 기본 식별 정보:
page_type: (COVER / BODY / OUTRO 중 택 1, 이미지 내용 기반 판단)

2. 텍스트 콘텐츠 분석 (OCR 및 구조화):
main_title: (가장 핵심적인 대제목 텍스트)
sub_title: (부제 또는 보조 설명 텍스트, 없으면 null)
body_text_summary: (본문 내용의 핵심 요약)
tone_and_manner: (텍스트에서 느껴지는 전반적인 어조. 예: 친근한, 공식적인, 긴급한, 감성적인)
keywords: (콘텐츠를 대표하는 핵심 키워드 3~5개)

3. 디자인 및 스타일 분석 (Visual Analysis):
visual_vibe: (이미지가 주는 시각적 분위기. 예: 활기찬, 차분한, 신뢰감 있는, 경쾌한)
layout_feature: (텍스트와 이미지의 배치 특징. 예: 상단 제목 집중형, 좌우 2단 분할형, 중앙 이미지 강조형)
color_palette_feel: (주요 색상 조합이 주는 느낌. 예: 파란색 계열의 전문성, 노란색/주황색의 따뜻함)

4. 출력 형식 지정:
"위 분석 결과를 반드시 아래와 같은 단일 JSON 객체 형식으로만 출력하시오."
{
  "page_type": "COVER",
  "main_title": "제목",
  "sub_title": "부제",
  "body_text_summary": "요약",
  "tone_and_manner": "어조",
  "keywords": ["키워드1", "키워드2"],
  "visual_vibe": "분위기",
  "layout_feature": "레이아웃",
  "color_palette_feel": "색상느낌"
}
"""

def setup_api():
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    genai.configure(api_key=API_KEY)

def analyze_image(model, image_path):
    try:
        img = Image.open(image_path)
        response = model.generate_content([SYSTEM_PROMPT, ANALYSIS_PROMPT, img])
        
        # Extract JSON from response
        text = response.text
        # Simple cleanup to find JSON block if wrapped in markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        parsed = json.loads(text.strip())
        
        if isinstance(parsed, list):
            if len(parsed) > 0 and isinstance(parsed[0], dict):
                return parsed[0]
            else:
                raise ValueError(f"Expected dict, got list: {parsed}")
        elif isinstance(parsed, dict):
            return parsed
        else:
            raise ValueError(f"Expected dict, got {type(parsed)}")

    except Exception as e:
        error_msg = f"Error analyzing {image_path}: {e}\n"
        print(error_msg)
        with open("error.log", "a", encoding="utf-8") as err_f:
            err_f.write(error_msg)
        return None

def main():
    setup_api()
    model = genai.GenerativeModel(MODEL_NAME)
    
    # Check if output file exists to resume? 
    # For now, we'll just append. If it's a fresh run, user should delete the file.
    # Or we can read existing to skip.
    processed_files = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if "file_name" in data:
                        processed_files.add(data["file_name"])
                except:
                    pass
    
    print(f"Found {len(processed_files)} already processed images.")

    total_images = []
    for type_name, folder_path in DIR_MAP.items():
        if not os.path.exists(folder_path):
            print(f"Warning: Folder not found: {folder_path}")
            continue
            
        # Support multiple extensions
        files = []
        for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
            files.extend(glob.glob(os.path.join(folder_path, ext)))
        
        print(f"Found {len(files)} images in {type_name} ({folder_path})")
        
        for file_path in files:
            file_name = os.path.basename(file_path)
            if file_name in processed_files:
                continue
                
            total_images.append((type_name, file_path, file_name))

    print(f"Starting analysis for {len(total_images)} new images...")
    
    # Apply Test Limit
    if TEST_LIMIT and len(total_images) > TEST_LIMIT:
        print(f"Test mode: Limiting to {TEST_LIMIT} images.")
        total_images = total_images[:TEST_LIMIT]

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for type_name, file_path, file_name in tqdm(total_images):
            result = analyze_image(model, file_path)
            
            if result:
                # Add metadata
                result["file_name"] = file_name
                result["file_path"] = file_path # Optional: absolute path
                result["original_type_folder"] = type_name
                
                # Write to file immediately
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
                f.flush() # Ensure it's written
                
            # Rate limiting / Sleep to avoid hitting limits too hard if needed
            # Flash is fast, but let's be safe.
            time.sleep(1) 

if __name__ == "__main__":
    main()
