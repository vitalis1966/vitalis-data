import pdfplumber, requests, csv, os, re, io
from datetime import datetime, timedelta

HEALTH_KEYWORDS = [
    "medical", "dental", "clinic", "health", "pharmacy", "optom",
    "veterinary", "vet ", "physician", "doctor", "surgical",
    "imaging", "diagnostic", "laboratory", "physio", "chiro",
    "massage", "therapy", "therapist", "hospital", "care centre",
    "care center", "wellness", "rehabilitation", "rehab",
]

def is_health(text):
    t = text.lower()
    return any(kw in t for kw in HEALTH_KEYWORDS)

MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

today = datetime.utcnow()
pdf_urls = []
for days_back in range(7):
    d = today - timedelta(days=days_back)
    if d.weekday() >= 5:
        continue
    month_name = MONTHS[d.month - 1]
    folder = f"{d.year}-{d.month:02d}"
    filename = f"{month_name}-{d.day}-{d.year}.pdf"
    url = f"https://www.burnaby.ca/sites/default/files/acquiadam/{folder}/{filename}"
    pdf_urls.append(url)

print(f"Generated {len(pdf_urls)} PDF URLs to check")

os.makedirs("burnaby", exist_ok=True)
all_rows = []

for pdf_url in pdf_urls:
    print(f"Processing: {pdf_url}")
    try:
        r = requests.get(pdf_url, timeout=60)
        if not r.ok:
            print(f"  HTTP {r.status_code} — skipping")
            continue

        date_match = re.search(r'(\d{4}-\d{2})/\w+-(\d+)-(\d{4})\.pdf', pdf_url)
        month_folder = date_match.group(1) if date_match else "unknown"
        day = date_match.group(2) if date_match else "?"
        permit_date = f"{month_folder}-{int(day):02d}"

        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                # Split into permit blocks — each starts with a permit number BLDxx-xxxxx
                blocks = re.split(r'(?=BLD\d{2}-\d{5})', text)

                for block in blocks:
                    if not block.strip() or not re.search(r'BLD\d{2}-\d{5}', block):
                        continue

                    lines = block.strip().split('\n')

                    # Extract permit number
                    permit_match = re.search(r'(BLD\d{2}-\d{5})', block)
                    permit_number = permit_match.group(1) if permit_match else ""

                    # Extract description (text after "Description" label)
                    desc_match = re.search(r'Description\s*\n(.+?)(?:\n[A-Z]|\Z)', block, re.DOTALL)
                    description = desc_match.group(1).strip() if desc_match else ""

                    # Extract value of work
                    value_match = re.search(r'\$[\d,]+\.\d{2}', block)
                    value = value_match.group(0) if value_match else ""

                    # Extract address — prefer street pattern, fall back to first line
                    # Site address appears in the page text immediately BEFORE the permit number
                    # Extract from original page text, not from the block
                    permit_pos = text.find(permit_number)
                    address = ""
                    if permit_pos > 0:
                        pre_text = text[:permit_pos].strip()
                        pre_lines = [l.strip() for l in pre_text.split('\n') if l.strip()]
                        if pre_lines:
                            address = pre_lines[-1]  # last line before permit number

                    # Check if health-related (check full block text)
                    if is_health(block):
                        all_rows.append({
                            "permit_date": permit_date,
                            "address": address,
                            "permit_number": permit_number,
                            "description": description,
                            "value_of_work": value,
                            "full_text": block.strip()[:500],
                            "source_url": pdf_url,
                        })
                        print(f"  MATCH: {permit_number} — {address} — {description[:80]}")

    except Exception as e:
        print(f"  Error: {e}")

print(f"\nHealth-related permits found: {len(all_rows)}")

outfile = "burnaby/BuildingPermits.csv"
fieldnames = ["permit_date","address","permit_number","description",
              "value_of_work","full_text","source_url"]

existing = set()
if os.path.exists(outfile):
    with open(outfile, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing.add(row.get("permit_number",""))

new_rows = [r for r in all_rows if r["permit_number"] not in existing]
print(f"New rows to add: {len(new_rows)}")

write_header = not os.path.exists(outfile)
with open(outfile, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    if write_header:
        writer.writeheader()
    writer.writerows(new_rows)

print(f"Done. Total rows: {sum(1 for _ in open(outfile)) - 1}")