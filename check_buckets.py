from supabase import create_client, Client

SUPABASE_URL = "https://liqozdnssagjotfbdibo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxpcW96ZG5zc2Fnam90ZmJkaWJvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NDUxMzA2NSwiZXhwIjoyMDgwMDg5MDY1fQ.HCQgqSlShncV8OlPKwGpzn-DNPZxFmA5Llja50xCll4"

def list_buckets():
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    try:
        buckets = supabase.storage.list_buckets()
        print("✅ Buckets found:")
        for b in buckets:
            print(f" - {b.name}")
    except Exception as e:
        print(f"❌ Failed to list buckets: {e}")

if __name__ == "__main__":
    list_buckets()
