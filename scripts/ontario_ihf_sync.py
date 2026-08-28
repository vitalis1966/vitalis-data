import requests, csv, os, io
from datetime import datetime

CSV_URL = (
    "https://data.ontario.ca/dataset/aac6695e-a8c0-4e0b-ae47-55f3a840ec21"
    "/resource/b5a7c09f-99a7-4f88-9c15-87d69acdf888"
    "/download/ichsc_web_page_report_march_2026.csv"
)

# Services worth targeting — diagnostic imaging, surgical, specialist
TARGET_SERVICES = [
    "radiography", "ultrasound", "mammography", "mri", "magnetic resonance",
    "computed tomography", "ct", "nuclear medicine", "fluoroscopy",
    "vascular", "cardiology", "cardiac", "endoscopy", "colonoscopy",
    "pulmonary", "sleep", "fertility", "ophthalmology", "ophthalmic",
    "plastic surgery", "dialysis", "bone mineral", "positron emission",
]

# Exclude mobile-only and hospital-based (not independent clinics)
EXCLUDE_SERVICES = ["mobile radiography", "mobile general ultrasound", "mobile vascular"]

# Dave's target cities
TARGET_CITIES = {
    "toronto", "north york", "etobicoke", "scarborough", "east york",
    "hamilton", "ottawa", "london", "mississauga", "brampton",
    "kitchener", "waterloo", "cambridge", "burlington", "oakville",
    "markham", "vaughan", "richmond hill", "newmarket", "oshawa",
    "ajax", "whitby", "pickering", "nepean", "kanata", "orleans",
    "ancaster", "stoney creek", "dundas", "grimsby",
}

def is_target(row):
    city = row.get("CITY", "").lower().strip()
    services = row.get("SERVICES", "").lower()
    if city not in TARGET_CITIES:
        return False
    # Exclude purely mobile operations
    if all(ex in services for ex in EXCLUDE_SERVICES) and "radiography" not in services.replace("mobile radiography", ""):
        return False
    return any(svc in services for svc in TARGET_SERVICES)

print("Downloading ICHSC CSV...")
r = requests.get(CSV_URL, timeout=60)
r.raise_for_status()
print(f"Downloaded {len(r.content):,} bytes")

reader = csv.DictReader(io.StringIO(r.text))
all_rows = list(reader)
print(f"Total records: {len(all_rows)}")

filtered = [row for row in all_rows if is_target(row)]
print(f"Target city + service matches: {len(filtered)}")

os.makedirs("ontario-ihf", exist_ok=True)
outfile = "ontario-ihf/Facilities.csv"

fieldnames = [
    "licence_num", "facility_name", "address", "address2", "city",
    "province", "postal_code", "phone", "licensee_name", "services",
    "assess_date", "action_date", "action_comment"
]

with open(outfile, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in filtered:
        writer.writerow({
            "licence_num":     row.get("LICENCE_NUM", ""),
            "facility_name":   row.get("FACILITYNAME", ""),
            "address":         row.get("ADDRESS1", ""),
            "address2":        row.get("ADDRESS2", ""),
            "city":            row.get("CITY", ""),
            "province":        row.get("PROVINCE", "ON"),
            "postal_code":     row.get("POSTAL_CODE", ""),
            "phone":           row.get("PHONE_NUM", ""),
            "licensee_name":   row.get("LICENSEE_NAME", ""),
            "services":        row.get("SERVICES", ""),
            "assess_date":     row.get("ASSESS_DATE", ""),
            "action_date":     row.get("ACTION_DATE", ""),
            "action_comment":  row.get("ACTION_COMMENT", ""),
        })

total = sum(1 for _ in open(outfile)) - 1
print(f"Done. {total} facilities written to {outfile}")

# Print city breakdown
from collections import Counter
cities = Counter(row.get("CITY", "") for row in filtered)
print("\nBy city:")
for city, count in sorted(cities.items(), key=lambda x: -x[1])[:15]:
    print(f"  {city}: {count}")