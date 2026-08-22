import requests
import json
import uuid

URL = "https://gdx-api.costco.com/catalog/search/api/v1/search"

payload = {
    "visitorId": "81593075349571012370904879373705132128",
    "query": "jack daniel's 10 year",
    "pageSize": 24,
    "offset": 0,
    "orderBy": None,
    "searchMode": "page",
    "personalizationEnabled": True,
    "warehouseId": "471-wh",
    "shipToPostal": "95765",
    "shipToState": "CA",
    "deliveryLocations": [
        "653-bd", "893-bd", "471-wh", "1251-3pl",
        "1321-wm", "1479-3pl", "283-wm", "561-wm",
        "725-wm", "731-wm", "758-wm", "759-wm",
        "847_0-cor", "847_0-cwt", "847_0-edi",
        "847_0-ehs", "847_0-membership", "847_0-mpt",
        "847_0-spc", "847_0-wm", "847_1-cwt",
        "847_1-edi", "847_aa_00-spc", "847_aa_u610-edi",
        "847_bosch_1472-edi", "847_d-fis", "847_ge_sac-edi",
        "847_lg_n1f-edi", "847_lux_us51-edi",
        "847_NA-cor", "847_NA-pharmacy", "847_NA-wm",
        "847_ss_u357-edi", "847_wp_r460-edi",
        "951-wm", "952-wm", "9847-wcs"
    ],
    "filterBy": ["HIDE_OUT_OF_STOCK"],
    "pageCategories": []
}

headers = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Content-Type": "application/json",
    "Origin": "https://www.costco.com",
    "Referer": "https://www.costco.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),

    # These were present in the actual Costco browser request.
    "client-identifier": "168287ea-1201-45f6-9b45-5bbea49f8ee7",
    "client_id": "USBC",
    "locale": "en-US",
    "searchResultProvider": "GRS",

    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

print("=" * 70)
print("COSTCO BOURBON RADAR - CHROME REQUEST REPRODUCTION")
print("=" * 70)
print()
print("Search:", payload["query"])
print("Warehouse:", payload["warehouseId"])
print("ZIP:", payload["shipToPostal"])
print()

try:
    response = requests.post(
        URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    print("HTTP status:", response.status_code)
    print("Response length:", len(response.text))
    print()
    print("RESPONSE:")
    print(response.text[:30000])

except Exception as e:
    print("ERROR:", repr(e))

print()
print("=" * 70)
print("SEARCH TEST COMPLETE")
print("=" * 70)
