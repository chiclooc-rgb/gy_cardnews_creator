import os
import glob
import json
from supabase import create_client, Client
from tqdm import tqdm
import mimetypes

# Configuration
from dotenv import load_dotenv

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://liqozdnssagjotfbdibo.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    print("⚠️ SUPABASE_KEY not found in environment variables.")
    # Fallback for user input if needed, or just error out
    
BUCKET_NAME = "cardnews"

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "sorted_output", "img")
URL_MAP_FILE = os.path.join(SCRIPT_DIR, "supabase_url_map.json")

DIR_MAP = {
    "COVER": os.path.join(BASE_DIR, "10_gy_cover"),
    "BODY": os.path.join(BASE_DIR, "10_gy_body"),
    "OUTRO": os.path.join(BASE_DIR, "10_gy_outro"),
}

def upload_file(file_path, storage_path):
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'
            
        with open(file_path, 'rb') as f:
            response = supabase.storage.from_(BUCKET_NAME).upload(
                path=storage_path,
                file=f,
                file_options={"content-type": mime_type, "upsert": "false"} 
            )
        return True
    except Exception as e:
        # If error is "The resource already exists", we can skip or ignore
        if "The resource already exists" in str(e) or "Duplicate" in str(e):
            return True # Treat as success
        print(f"❌ Upload failed for {file_path}: {e}")
        return False

def get_public_url(storage_path):
    return supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)

def main():
    print("🚀 Starting Supabase Upload...")
    
    url_map = {}
    if os.path.exists(URL_MAP_FILE):
        with open(URL_MAP_FILE, 'r', encoding='utf-8') as f:
            url_map = json.load(f)
            
    total_files = []
    for type_name, folder_path in DIR_MAP.items():
        if not os.path.exists(folder_path):
            continue
        
        files = []
        for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
            files.extend(glob.glob(os.path.join(folder_path, ext)))
            
        for file_path in files:
            total_files.append((type_name, file_path))
            
    print(f"📋 Found {len(total_files)} images to process.")
    
    success_count = 0
    skip_count = 0
    
    for type_name, file_path in tqdm(total_files):
        file_name = os.path.basename(file_path)
        
        # Storage path: e.g., COVER/img.jpg
        storage_path = f"{type_name}/{file_name}"
        
        # Check if already mapped
        if file_name in url_map:
            skip_count += 1
            continue
            
        # Upload
        if upload_file(file_path, storage_path):
            # Get Public URL
            public_url = get_public_url(storage_path)
            url_map[file_name] = public_url
            success_count += 1
        
        # Save map periodically
        if success_count % 10 == 0:
             with open(URL_MAP_FILE, 'w', encoding='utf-8') as f:
                json.dump(url_map, f, ensure_ascii=False, indent=2)

    # Final save
    with open(URL_MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(url_map, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Upload Complete!")
    print(f"   - Uploaded: {success_count}")
    print(f"   - Skipped (Already mapped): {skip_count}")
    print(f"   - Map saved to: {URL_MAP_FILE}")

if __name__ == "__main__":
    main()
