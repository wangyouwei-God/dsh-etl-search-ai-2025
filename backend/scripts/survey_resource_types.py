
import requests
import json
import random
import sys

# Sample IDs from the file
SAMPLE_IDS = [
    "be0bdc0e-bc2e-4f1d-b524-2c02798dd893",
    "755e0369-f8db-4550-aabe-3f9c9fbcb93d",
    "1c4f835c-d243-4593-a9b4-71410b9b4bf0"
]

def fetch_and_analyze(uuid):
    # Strategy 1: Try base URL (Content Negotiation)
    base_url = f"https://catalogue.ceh.ac.uk/id/{uuid}"
    print(f"\n--- Analyzing {uuid} ---")
    print(f"Strategy 1: Requesting Base URL {base_url}")
    try:
        # Try asking for JSON
        headers = {'Accept': 'application/json'}
        response = requests.get(base_url, headers=headers, timeout=10, allow_redirects=True)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            print(f"Content-Type: {content_type}")
            if 'json' in content_type:
                data = response.json()
                print("SUCCESS: JSON received via Content Negotiation")
                print(f"Title: {data.get('title', 'Unknown')}")
                scan_keys(data)
                return
            else:
                print("Received non-JSON content. First 200 chars:")
                print(response.text[:200])

    except Exception as e:
        print(f"Strategy 1 Failed: {e}")

    # Strategy 2: Check WAF pattern (gemini xml)
    waf_url = f"https://catalogue.ceh.ac.uk/documents/gemini/waf/{uuid}.xml"
    print(f"Strategy 2: Requesting WAF URL {waf_url}")
    try:
        response = requests.get(waf_url, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS: XML found in WAF")
            print(response.text[:200])
    except Exception as e:
        print(f"Strategy 2 Failed: {e}")

def scan_keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            if 'url' in k.lower() or 'download' in k.lower() or 'file' in k.lower():
                if isinstance(v, str) and v.startswith('http'):
                    print(f"  Found potential resource at {new_path}: {v}")
            scan_keys(v, new_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            scan_keys(item, f"{path}[{i}]")

if __name__ == "__main__":
    print("Starting Resource Type Survey...")
    for uuid in SAMPLE_IDS:
        fetch_and_analyze(uuid)
