#!/usr/bin/env python3
"""Test RAG Chat functionality"""

import os
import sys
from pathlib import Path

import requests

USE_TESTCLIENT = os.environ.get("USE_TESTCLIENT") == "1"

if USE_TESTCLIENT:
    sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))
    from fastapi.testclient import TestClient
    from api.main import app
    import atexit

    client = TestClient(app)
    client.__enter__()
    atexit.register(lambda: client.__exit__(None, None, None))

    def http_post(path, **kwargs):
        return client.post(path, **kwargs)
else:
    def http_post(path, **kwargs):
        return requests.post(f"http://localhost:8000{path}", **kwargs)

def test_chat():
    messages = [
        "What datasets do you have about river flow?",
        "Tell me about soil moisture data",
        "Do you have any climate data?"
    ]

    print("Testing RAG Chat Endpoint...")
    print("="*60)

    for msg in messages:
        print(f"\n>>> User: {msg}")

        try:
            response = http_post(
                "/api/chat",
                json={"message": msg},
                timeout=45
            )

            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', data.get('response', ''))
                print(f"<<< Assistant: {answer[:300]}...")

                if 'context_datasets' in data:
                    print(f"\nContext: {len(data['context_datasets'])} datasets used")
                elif 'contexts' in data:
                    print(f"\nContext: {len(data['contexts'])} contexts used")

                print(f"✓ Response received")
            else:
                print(f"✗ Error {response.status_code}: {response.text[:200]}")

        except requests.exceptions.Timeout:
            print("⚠ Timeout (>45s) - Model may be slow or not configured")
        except Exception as e:
            print(f"✗ Error: {str(e)}")

    print("\n" + "="*60)
    print("Chat test complete")

if __name__ == "__main__":
    test_chat()
