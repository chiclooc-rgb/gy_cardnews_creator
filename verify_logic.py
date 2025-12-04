from supabase import create_client, Client
import json
import requests

SUPABASE_URL = "https://liqozdnssagjotfbdibo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxpcW96ZG5zc2Fnam90ZmJkaWJvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NDUxMzA2NSwiZXhwIjoyMDgwMDg5MDY1fQ.HCQgqSlShncV8OlPKwGpzn-DNPZxFmA5Llja50xCll4"

def get_signed_url(path):
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    try:
        # Create signed URL valid for 1 hour (3600 seconds)
        res = supabase.storage.from_("cardnews").create_signed_url(path, 3600)
        # res is a dict or object depending on version. Usually dict {'signedURL': ...} or object.
        # supabase-py v2 returns dict or object? Let's print it to be sure.
        print(f"🔑 Signed URL Response: {res}")
        if isinstance(res, dict) and 'signedURL' in res:
            return res['signedURL']
        elif hasattr(res, 'signedURL'): # Pydantic model
            return res.signedURL
        # Fallback for older versions or different response structure
        return str(res) 
    except Exception as e:
        print(f"❌ Failed to create signed URL: {e}")
        return None

def test_maedori_logic():
    print("🧪 Testing Maedori Logic...")
    
    # Mock Data
    page_data = {"summary": ["광양시 공식 마스코트 매돌이가 소개합니다."]}
    page_data_str = json.dumps(page_data, ensure_ascii=False)
    
    prompt_parts = []
    
    # Logic from app.py
    has_maedori = False
    if "매돌이" in page_data_str:
        has_maedori = True
    
    if has_maedori:
        # Try Signed URL
        maedori_path = "assets/maedori_character.png"
        maedori_url = get_signed_url(maedori_path)
        
        if not maedori_url:
            print("❌ Failed to get signed URL")
            return

        prompt_parts.append("**[매돌이 공식 캐릭터 사용 규칙 (매우 중요 - 반드시 준수)]**")
        prompt_parts.append(f"규칙 2: ... URL: {maedori_url}")
        
    # Verification
    if has_maedori and any(maedori_url in p for p in prompt_parts):
        print("✅ Maedori logic detected correctly.")
        # Check URL validity
        try:
            response = requests.get(maedori_url)
            if response.status_code == 200:
                print("✅ Maedori URL is accessible.")
            else:
                print(f"❌ Maedori URL is NOT accessible (Status: {response.status_code})")
                print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Request failed: {e}")
    else:
        print("❌ Maedori logic FAILED.")

def test_symbol_logic():
    print("\n🧪 Testing Symbol Mark Logic...")
    
    symbol_path = "assets/gwangyang_symbol.png"
    symbol_url = get_signed_url(symbol_path)
    
    if not symbol_url:
        print("❌ Failed to get signed URL")
        return

    prompt_parts = []
    
    # Logic from app.py (Unconditional for now as per implementation)
    prompt_parts.append(f"... URL: {symbol_url}")
    
    # Verification
    if any(symbol_url in p for p in prompt_parts):
        print("✅ Symbol logic included.")
        # Check URL validity
        try:
            response = requests.get(symbol_url)
            if response.status_code == 200:
                print("✅ Symbol URL is accessible.")
            else:
                print(f"❌ Symbol URL is NOT accessible (Status: {response.status_code})")
                print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Request failed: {e}")
    else:
        print("❌ Symbol logic FAILED.")

if __name__ == "__main__":
    test_maedori_logic()
    test_symbol_logic()
