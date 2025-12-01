import os
import glob
import json
import time
import typing
import google.generativeai as genai
from PIL import Image
from tqdm import tqdm
import pickle
import numpy as np

# Configuration
# Try to get API Key from environment variable first, then fallback to hardcoded (security best practice)
API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyDXpLVPAb3rnWRoHE56B8OuGi_fxLHfzUE") 
MODEL_NAME = "gemini-2.0-flash" # Updated to 2.0-flash as per app.py, or keep 1.5-flash if preferred. Using 2.0-flash for consistency.
EMBEDDING_MODEL = "models/text-embedding-004"
OUTPUT_JSONL = "gwangyang_cardnews_db.jsonl"
OUTPUT_PKL = "gwangyang_style_index.pkl"

# Set BASE_DIR relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "sorted_output", "img")

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

def create_embeddings_and_pkl():
    print("\n🚀 Starting Embedding Generation & PKL Creation...")
    
    # Load Supabase URL Map
    url_map = {}
    url_map_file = os.path.join(SCRIPT_DIR, "supabase_url_map.json")
    if os.path.exists(url_map_file):
        with open(url_map_file, 'r', encoding='utf-8') as f:
            url_map = json.load(f)
        print(f"🌐 Loaded Supabase URL Map: {len(url_map)} entries")
    else:
        print("⚠️ Warning: supabase_url_map.json not found. Using local paths.")

    data_list = []
    if os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSONL, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data_list.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    else:
        print(f"❌ {OUTPUT_JSONL} not found. Cannot create embeddings.")
        return

    print(f"📋 Loaded {len(data_list)} items from JSONL.")
    
    final_index = []
    
    for item in tqdm(data_list, desc="Generating Embeddings"):
        try:
            # Construct text for embedding
            text_to_embed = f"""
            Page Type: {item.get('page_type', '')}
            Title: {item.get('main_title', '')}
            Keywords: {', '.join(item.get('keywords', []))}
            Vibe: {item.get('visual_vibe', '')}
            Layout: {item.get('layout_feature', '')}
            Colors: {item.get('color_palette_feel', '')}
            Tone: {item.get('tone_and_manner', '')}
            """
            
            # Generate embedding
            embedding = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=text_to_embed,
                task_type="retrieval_document"
            )['embedding']
            
            item['embedding'] = embedding
            
            # Update file_path to Supabase URL if available
            file_name = item.get('file_name')
            if file_name and file_name in url_map:
                item['file_path'] = url_map[file_name]
            else:
                # Fallback to relative path logic if not in map
                abs_path = item.get('file_path', '')
                if abs_path and os.path.exists(abs_path):
                    try:
                        rel_path = os.path.relpath(abs_path, SCRIPT_DIR)
                        item['file_path'] = rel_path
                    except ValueError:
                        item['file_path'] = os.path.basename(abs_path)
            
            final_index.append(item)
            
            # Rate limit protection
            time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ Error generating embedding for {item.get('file_name')}: {e}")
            continue

    # Save to PKL
    with open(OUTPUT_PKL, 'wb') as f:
        pickle.dump(final_index, f)
    
    print(f"✅ Successfully saved {len(final_index)} items to {OUTPUT_PKL}")

def main():
    setup_api()
    model = genai.GenerativeModel(MODEL_NAME)
    
    # Check if output file exists to resume
    processed_files = set()
    if os.path.exists(OUTPUT_JSONL):
        with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
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

    # Skip image analysis as per user request, just rebuild PKL from existing JSONL
    # print(f"Starting analysis for {len(total_images)} new images...")
    
    # # Apply Test Limit
    # if TEST_LIMIT and len(total_images) > TEST_LIMIT:
    #     print(f"Test mode: Limiting to {TEST_LIMIT} images.")
    #     total_images = total_images[:TEST_LIMIT]

    # if total_images:
    #     with open(OUTPUT_JSONL, "a", encoding="utf-8") as f:
    #         for type_name, file_path, file_name in tqdm(total_images):
    #             result = analyze_image(model, file_path)
                
    #             if result:
    #                 # Add metadata
    #                 result["file_name"] = file_name
    #                 result["file_path"] = file_path # Save absolute path initially
    #                 result["original_type_folder"] = type_name
                    
    #                 # Write to file immediately
    #                 f.write(json.dumps(result, ensure_ascii=False) + "\n")
    #                 f.flush() # Ensure it's written
                    
    #             # Rate limiting
    #             time.sleep(1) 
    # else:
    #     print("No new images to analyze.")

    # After analysis (or if skipped), generate PKL
    create_embeddings_and_pkl()

if __name__ == "__main__":
    main()

