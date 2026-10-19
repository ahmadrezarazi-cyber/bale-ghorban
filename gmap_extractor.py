#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gmap_extractor.py — Google Maps -> CSV via Apify compass/crawler-google-places
Usage:
  export APIFY_TOKEN=apify_api_xxx
  python gmap_extractor.py --province اصفهان --limit 30 --out contacts_isfahan.csv
  python gmap_extractor.py --province اصفهان --city کاشان --limit 50
  python gmap_extractor.py --all --limit 20  # all cities Isfahan province

Output CSV: phone,name,category,city,province,address,rating,reviews,mapsUrl
Phone normalized to 09... (Iran). Only mobiles kept unless --keep-all.
"""
import argparse, csv, json, re, sys, time
from pathlib import Path

ISFAHAN_CITIES = [
    "اصفهان","کاشان","نجف‌آباد","خمینی‌شهر","شاهین‌شهر","فولادشهر","شهرضا","مبارکه",
    "نطنز","اردستان","گلپایگان","خوانسار","سمیرم","دهاقان","فلاورجان","لنجان",
    "نایین","تیران","فریدن","فریدونشهر","چادگان","بویین و میاندشت","میمه","ورزنه",
    "کوهپایه","داران","برخوار",
]

CATEGORIES = [
    "عمده فروشی حبوبات",
    "پخش مواد غذایی عمده",
    "بنکداری مواد غذایی",
    "کترینگ",
    "تهیه غذای آماده",
    "آشپزخانه صنعتی",
    "رستوران",
    "پخش برنج عمده",
]

def normalize_phone(raw: str) -> str:
    if not raw: return ""
    s = re.sub(r"[\s\-()]", "", raw.strip())
    s = s.replace("+98","0").replace("0098","0")
    pers = "۰۱۲۳۴۵۶۷۸۹"
    lat  = "0123456789"
    tr = str.maketrans(pers+ "٠١٢٣٤٥٦٧٨٩", lat+lat)
    s = s.translate(tr)
    m = re.search(r"(0?9\d{9})", s)
    if m:
        num = m.group(1)
        if not num.startswith("0"):
            num = "0"+num
        if len(num)==11 and num.startswith("09"):
            return num
    digits = re.sub(r"\D","", s)
    if len(digits)>=11:
        tail = digits[-11:]
        if tail.startswith("09"):
            return "0"+tail[1:] if not tail.startswith("0") else tail
        if tail.startswith("9"):
            tail = "0"+tail
            if tail.startswith("09"):
                return tail
    return ""

def phone_is_mobile(phone: str) -> bool:
    return phone.startswith("09") and len(phone)==11 and phone[2] in "1239"

def run_apify(token: str, queries: list, location: str, max_places: int, language="fa"):
    from apify_client import ApifyClient
    client = ApifyClient(token)
    actor_input = {
        "searchStringsArray": queries,
        "locationQuery": location,
        "maxCrawledPlacesPerSearch": max_places,
        "language": language,
        "searchMatching": "all",
        "placeMinimumStars": "",
        "priceLevels": [],
        "website": "allPlaces",
        "skipClosedPlaces": False,
        "scrapeContacts": True,
        "scrapeImageAuthors": False,
        "scrapeReviewerName": False,
        "scrapeReviewerUrl": False,
        "scrapeReviewUrl": False,
    }
    print(f"[Apify] {location} queries={queries} max={max_places}", flush=True)
    run = client.actor("compass/crawler-google-places").call(run_input=actor_input)
    # Apify client 3.x returns Run object, not dict
    if isinstance(run, dict):
        dataset_id = run.get("defaultDatasetId")
    else:
        dataset_id = getattr(run, "defaultDatasetId", None) or getattr(run, "default_dataset_id", None) or (run.get("defaultDatasetId") if hasattr(run, "get") else None)
    if not dataset_id:
        # Fallback try dict access
        try:
            dataset_id = run["defaultDatasetId"]
        except:
            pass
    if not dataset_id:
        print(f"No dataset for {location} (run={run})", flush=True)
        return []
    items = list(client.dataset(dataset_id).iterate_items())
    print(f"[Apify] {location} -> {len(items)} items", flush=True)
    return items

def detect_category(it):
    # Try to recover which query matched
    for f in ("searchString","searchQuery","searchTerm"):
        v = it.get(f)
        if v: return v.strip()
    return ""

def items_to_rows(items, province, city, category):
    rows=[]
    for it in items:
        # Use detected category if passed as single bulk, else given category
        cat = detect_category(it) or category
        name = (it.get("title") or it.get("name") or "").strip()
        phone_raw = it.get("phone") or it.get("phoneNumber") or it.get("phoneUnformatted") or ""
        if not phone_raw and it.get("placeContact"):
            phone_raw = it["placeContact"]
        if isinstance(phone_raw, list):
            phone_raw = phone_raw[0] if phone_raw else ""
        phone = normalize_phone(str(phone_raw))
        address = (it.get("address") or it.get("formattedAddress") or "").strip()
        rating = it.get("totalScore") or it.get("rating") or ""
        reviews = it.get("reviewsCount") or it.get("reviews") or ""
        maps_url = it.get("url") or it.get("placeId") or ""
        if isinstance(maps_url, str) and maps_url.startswith("ChIJ"):
            maps_url = f"https://www.google.com/maps/place/?q=place_id:{maps_url}"
        rows.append({
            "phone": phone,
            "phone_raw": str(phone_raw)[:40],
            "name": name,
            "category": cat,
            "city": city,
            "province": province,
            "address": address,
            "rating": str(rating),
            "reviews": str(reviews),
            "mapsUrl": maps_url,
        })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", default="اصفهان")
    ap.add_argument("--city", default="")
    ap.add_argument("--limit", type=int, default=30, help="max places per query")
    ap.add_argument("--out", default="")
    ap.add_argument("--token", default="")
    ap.add_argument("--keep-all", action="store_true", help="keep rows even without mobile")
    ap.add_argument("--all", dest="all_cities", action="store_true", help="all cities in province")
    args = ap.parse_args()

    import os
    token = args.token or os.environ.get("APIFY_TOKEN") or os.environ.get("APIFY_API_TOKEN") or ""
    token2 = os.environ.get("APIFY_TOKEN2") or ""
    if not token:
        print("APIFY_TOKEN missing: export APIFY_TOKEN=apify_api_...")
        sys.exit(1)

    cities = [args.city] if args.city else (ISFAHAN_CITIES if args.all_cities or not args.city else ISFAHAN_CITIES)
    if not args.city and not args.all_cities:
        cities = ["اصفهان"]

    out_path = Path(args.out) if args.out else Path(f"contacts_{args.province}_{int(time.time())}.csv")
    all_rows=[]
    for city in cities:
        location = f"{city}, {args.province}, Iran"
        try:
            items = run_apify(token, CATEGORIES, location, args.limit, language="fa")
            rows = items_to_rows(items, args.province, city, "")
            print(f"  {city} | bulk {len(CATEGORIES)} cats: {len(rows)} raw, mobiles={sum(1 for r in rows if phone_is_mobile(r['phone']))}", flush=True)
            all_rows.extend(rows)
            time.sleep(2)
        except Exception as e:
            print(f"  FAIL {city}: {e}", flush=True)
            # Fallback to secondary token if available
            if 'token2' in locals() and token2 and 'charge' in str(e).lower():
                try:
                    items = run_apify(token2, CATEGORIES, location, args.limit, language="fa")
                    rows = items_to_rows(items, args.province, city, "")
                    print(f"  {city} | retry token2: {len(rows)} raw", flush=True)
                    all_rows.extend(rows)
                except Exception as e2:
                    print(f"  FAIL token2 {city}: {e2}", flush=True)

    seen=set()
    dedup=[]
    for r in all_rows:
        ph = r["phone"]
        if not args.keep_all and not phone_is_mobile(ph):
            continue
        if ph in seen:
            continue
        seen.add(ph)
        dedup.append(r)

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["phone","name","category","city","province","address","rating","reviews","mapsUrl","phone_raw"])
        w.writeheader()
        w.writerows(dedup)

    mobiles = sum(1 for r in dedup if phone_is_mobile(r["phone"]))
    print(f"\nDone: {len(all_rows)} raw -> {len(dedup)} dedup ({mobiles} mobiles) -> {out_path}", flush=True)
    bale_path = out_path.with_name(out_path.stem + "_bale.csv")
    with open(bale_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        for r in dedup:
            w.writerow([r["phone"], f"{r['name']} - {r['city']}"])
    print(f"Bale CSV: {bale_path} ({len(dedup)} rows)", flush=True)

if __name__ == "__main__":
    main()
