import requests
import json

SEARCH_URL = "https://gdx-api.costco.com/catalog/search"

payload = {
    "query": "Jack Daniel's 10 Year",
    "pageSize": 24,
    "offset": 0
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://www.costco.com",
    "Referer": "https://www.costco.com/",
}

print("=" * 60)
print("COSTCO BOURBON RADAR - PRODUCT SEARCH TEST")
print("=" * 60)
print()

try:
    response = requests.post(
        SEARCH_URL,
        json=payload,
        headers=headers,
        timeout=30
    )

    print("URL:", SEARCH_URL)
    print("HTTP status:", response.status_code)
    print("Response length:", len(response.text))
    print()

    if response.text:
        try:
            data = response.json()
            print(json.dumps(data, indent=2)[:15000])
        except Exception:
            print(response.text[:15000])
    else:
        print("EMPTY RESPONSE")

except Exception as e:
    print("REQUEST ERROR:", repr(e))

print()
print("PRODUCT SEARCH TEST COMPLETE")
