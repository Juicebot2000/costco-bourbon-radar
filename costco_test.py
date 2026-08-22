import requests
import json

URL = "https://gdx-api.costco.com/catalog/search/api/v1/search"

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
    "Referer": "https://www.costco.com/"
}

print("=" * 70)
print("COSTCO BOURBON RADAR - LIVE SEARCH")
print("=" * 70)
print()
print("Endpoint:", URL)
print("Search:", payload["query"])
print()

try:
    response = requests.post(
        URL,
        json=payload,
        headers=headers,
        timeout=30
    )

    print("HTTP status:", response.status_code)
    print("Response length:", len(response.text))
    print()

    print("RESPONSE:")
    print(response.text[:15000])

except Exception as e:
    print("ERROR:", repr(e))

print()
print("=" * 70)
print("SEARCH TEST COMPLETE")
print("=" * 70)
