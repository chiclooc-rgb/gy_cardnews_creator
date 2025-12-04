import os
from supabase import create_client, Client
from pathlib import Path

# Supabase Credentials (Hardcoded for this script execution as secrets.toml write failed)
SUPABASE_URL = "https://liqozdnssagjotfbdibo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxpcW96ZG5zc2Fnam90ZmJkaWJvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NDUxMzA2NSwiZXhwIjoyMDgwMDg5MDY1fQ.HCQgqSlShncV8OlPKwGpzn-DNPZxFmA5Llja50xCll4"
BUCKET_NAME = "cardnews"

def upload_file(supabase: Client, file_path: Path, destination_path: str):
    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        # Check if file exists
        try:
            supabase.storage.from_(BUCKET_NAME).get_public_url(destination_path)
            # If we want to overwrite, we might need to remove first or use upsert if supported/configured
            # For now, let's try to upload and see if it fails or overwrites
        except:
            pass

        response = supabase.storage.from_(BUCKET_NAME).upload(
            path=destination_path,
            file=file_bytes,
            file_options={"content-type": "image/png", "upsert": "true"}
        )
        
        # Get Public URL
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(destination_path)
        print(f"✅ Uploaded {file_path.name} to {destination_path}")
        print(f"   URL: {public_url}")
        return public_url
    except Exception as e:
        print(f"❌ Failed to upload {file_path.name}: {e}")
        return None

def main():
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Define assets to upload
    assets = [
        {
            "path": Path("251127-5 카드뉴스 기획+생성 런처/매돌이 이미지/매돌이-참고자료-모음.png"),
            "dest": "assets/maedori_character.png"
        },
        {
            "path": Path("광양시 심볼마크/광양시 심볼(배경투명화).png"),
            "dest": "assets/gwangyang_symbol.png"
        }
    ]
    
    print("🚀 Starting Asset Upload...")
    
    for asset in assets:
        if asset["path"].exists():
            upload_file(supabase, asset["path"], asset["dest"])
        else:
            print(f"⚠️ File not found: {asset['path']}")

if __name__ == "__main__":
    main()
