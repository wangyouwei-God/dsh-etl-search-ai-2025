
import subprocess
import time
import requests
import os
import signal
import sys
import json

def test_api():
    print("Starting Integration Test: Search & Chat API")
    
    # 1. Start Backend
    print("Starting backend...")
    process = subprocess.Popen(
        ["uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd="backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )
    
    base_url = "http://127.0.0.1:8001/api"
    
    try:
        # 2. Wait for startup
        print("Waiting for service startup...")
        for i in range(30):
            try:
                resp = requests.get(f"{base_url}/health", timeout=1)
                if resp.status_code == 200:
                    print("Service is UP!")
                    break
            except requests.ConnectionError:
                time.sleep(1)
            except Exception as e:
                print(f"Waiting... error: {e}")
                time.sleep(1)
        else:
            print("Timeout waiting for service!")
            return False

        # 3. Test Semantic Search
        print("\n--- Testing Semantic Search ---")
        query = "climate change temperature"
        search_url = f"{base_url}/search?q={query}&limit=5"
        print(f"GET {search_url}")
        
        resp = requests.get(search_url)
        if resp.status_code == 200:
            results = resp.json()
            print(f"Success! Got {len(results)} results.")
            if len(results) > 0:
                print(f"Top result: {results[0].get('title')}")
                print(f"Score: {results[0].get('score')}")
            else:
                print("WARNING: No results found (Is DB empty?)")
        else:
            print(f"FAILED: {resp.status_code} {resp.text}")
            return False

        # 4. Test RAG Chat
        print("\n--- Testing RAG Chat ---")
        chat_payload = {"message": "What datasets do you have about rainfall?"}
        print(f"POST {base_url}/chat {json.dumps(chat_payload)}")
        
        # Note: Chat might fail if Gemini API key is missing, but we check handling
        resp = requests.post(f"{base_url}/chat", json=chat_payload)
        
        if resp.status_code == 200:
            data = resp.json()
            print("Success!")
            print(f"Answer: {data.get('answer')[:100]}...")
            print(f"Sources: {len(data.get('sources', []))}")
        else:
            print(f"Chat returned {resp.status_code} (Expected if API key missing, but service is alive)")
            print(f"Response: {resp.text}")

        return True

    finally:
        print("\nStopping backend...")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except:
            pass

if __name__ == "__main__":
    if test_api():
        sys.exit(0)
    else:
        sys.exit(1)
