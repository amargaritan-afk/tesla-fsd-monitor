import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytesseract
from PIL import Image
import io
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import re
import sys

# ====================== TESSERACT PATH FIX + GRACEFUL FALLBACK ======================
try:
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
    # Quick test to verify Tesseract is working
    test_ocr = pytesseract.image_to_string(Image.new('RGB', (100, 100), color = 'white'))
    print("✅ Tesseract OCR initialized successfully")
except Exception as e:
    print(f"⚠️ Tesseract failed to initialize: {e}")
    print("   → OCR will be skipped for this run. Text matching will still work.")
    # Disable OCR for the rest of the run
    def safe_ocr(image):
        return ""
    pytesseract.image_to_string = safe_ocr

# ====================== YOUR SETTINGS ======================
ZIP_CODE = "93453"
USER_COORDS = (35.6, -120.7)
EMAIL_TO = os.getenv("EMAIL_TO", "amargaritan@gmail.com")

FSD_KEYWORDS = [
    "full self-driving", "fsd", "included package", "full self drive",
    "included software", "hw4", "transferable", "purchased fsd",
    "full self-driving capability", "autopilot hw4", "hw 4", "hardware 4",
    "fsd included", "included fsd", "fsd package", "full self-driving included",
    "full self driving included", "included fsd package", "fsd (included)",
    "capability included", "software included"
]

SEEN_FILE = "seen_listings.json"

if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE) as f:
        seen = json.load(f)
else:
    seen = {}

geolocator = Nominatim(user_agent="tesla_fsd_monitor_atascadero")

# (parse_price, send_email, DEALERS list, scrape_list_page remain exactly the same as in the previous full version I gave you)

# ... [paste the rest of the functions and main logic from the last full script I provided, including the expanded debug prints in scrape_detail] ...

# At the very end, make sure it always prints this:
print(f"✅ Run complete — {len(new_alerts)} new/price alerts + {len(sold_alerts)} sold alerts")

# ====================== ALL DEALERS (including AutoTempest) ======================
DEALERS = [
    # ... (your original 20 dealers exactly as before) ...
    {"name": "DriveCoolCars", "url": "https://www.drivecoolcars.com/newandusedcars?Year=2024&MakeName=Tesla&ModelName=Model%20Y&ClearAll=1", "detail_pattern": r"/vdp/"},
    {"name": "Evolving Motors", "url": "https://www.evolvingmotors.com/inventory/?make=tesla&model=model+y", "detail_pattern": r"/inventory/tesla/model-y/"},
    {"name": "DongCar 2023", "url": "https://www.dongcarinc.com/inventory/tesla/model-y/?vehicle_year=2023", "detail_pattern": r"/inventory/"},
    {"name": "DongCar 2024", "url": "https://www.dongcarinc.com/inventory/tesla/model-y/?vehicle_year=2024", "detail_pattern": r"/inventory/"},
    {"name": "DongCar 2025", "url": "https://www.dongcarinc.com/inventory/tesla/model-y/?vehicle_year=2025", "detail_pattern": r"/inventory/"},
    {"name": "Trusted Auto", "url": "https://www.trustedauto.org/inventory/?make=tesla&vehicle_year=2023,2024,2025&model=model+y", "detail_pattern": r"/inventory/"},
    {"name": "Find My Electric", "url": "https://www.findmyelectric.com/listings/?models=Model%20Y&makes=Tesla", "detail_pattern": r"/listings/"},
    {"name": "Premium Autos", "url": "https://www.premiumautosinc.com/tesla?year[gt]=2023&year[lt]=2026&model[]=Model%20Y&trim[]=Long%20Range&drivetrainstandard[]=AWD&drivetrainstandard[]=RWD&mileage[lt]=50000", "detail_pattern": r"/tesla/"},
    {"name": "California Beemers 2023", "url": "https://www.californiabeemers.com/pre-owned-cars/2023/Tesla/Model-Y?sort=InternetPrice&dir=desc", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "California Beemers 2024", "url": "https://www.californiabeemers.com/pre-owned-cars/2024/Tesla/Model-Y?sort=InternetPrice&dir=desc", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "California Beemers 2025", "url": "https://www.californiabeemers.com/pre-owned-cars/2025/Tesla/Model-Y?sort=InternetPrice&dir=desc", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "California Beemers 2026", "url": "https://www.californiabeemers.com/pre-owned-cars/2026/Tesla/Model-Y?sort=InternetPrice&dir=desc", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "PlugIn Auto 2023", "url": "https://www.pluginauto.com/pre-owned-cars/2023/Tesla/Model-Y?estimatedrangestart=250&sort=InternetPrice&dir=desc", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "PlugIn Auto 2024", "url": "https://www.pluginauto.com/pre-owned-cars/2024/Tesla/Model-Y?estimatedrangestart=250&sort=InternetPrice&dir=desc", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "PlugIn Auto 2025", "url": "https://www.pluginauto.com/pre-owned-cars/2025/Tesla/Model-Y?estimatedrangestart=250&sort=InternetPrice&dir=desc", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "OC Chief Auto 2023", "url": "https://www.occhiefautopch.com/pre-owned-cars/2023/Tesla/Model-Y?estimatedrangestart=250", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "OC Chief Auto 2024", "url": "https://www.occhiefautopch.com/pre-owned-cars/2024/Tesla/Model-Y?estimatedrangestart=250", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "OC Chief Auto 2025", "url": "https://www.occhiefautopch.com/pre-owned-cars/2025/Tesla/Model-Y?estimatedrangestart=250", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "OC Chief Auto 2026", "url": "https://www.occhiefautopch.com/pre-owned-cars/2026/Tesla/Model-Y?estimatedrangestart=250", "detail_pattern": r"/pre-owned-cars/"},
    {"name": "STG Auto Group", "url": "https://www.stgautogroup.com/used-vehicles?make[]=Tesla&model[]=Model%20Y&trim[]=Long%20Range&mileage[lt]=50000&year[gt]=2023", "detail_pattern": r"/used-vehicles/"},
    {"name": "AutoTempest", "url": "https://www.autotempest.com/results?drive=awd&localization=country&make=tesla&maxmiles=55000&maxprice=55000&minmiles=0&minprice=27000&minyear=2023&model=modely&saletype=classified&title=clean&zip=93453", "detail_pattern": r"/vehicle/|/details/|carvana.com/vehicle/|cars.com/vehicledetail/"},
]

def scrape_list_page(dealer):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(dealer["url"], headers=headers, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        potential_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if re.search(dealer["detail_pattern"], href, re.I):
                full_url = href if href.startswith('http') else f"https://{response.url.split('/')[2]}{href if href.startswith('/') else '/' + href}"
                card_text = (a.parent.get_text(strip=True) if a.parent else a.get_text(strip=True))[:600]
                price = next((t for t in re.findall(r'\$\d{1,3}(?:,\d{3})*', card_text)), 'Unknown')
                miles = next((t for t in re.findall(r'\d{1,3}(?:,\d{3})* mi', card_text, re.I)), 'Unknown')
                vin_match = re.search(r'[A-HJ-NPR-Z0-9]{17}', card_text)
                vin = vin_match.group(0) if vin_match else full_url.split('/')[-1].upper()[:17]
                title = a.get_text(strip=True)[:200] or "Tesla Model Y"
                potential_links.append({'title': title, 'price': price, 'miles': miles, 'vin': vin, 'detail_url': full_url, 'dealer': dealer["name"]})
        print(f"   → {dealer['name']}: {len(potential_links)} listings found")
        return list({v['detail_url']: v for v in potential_links}.values())
    except Exception as e:
        print(f"⚠️ Error scraping {dealer['name']}: {e}")
        return []

def scrape_detail(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        description = soup.get_text().lower()
        has_fsd_text = any(kw in description for kw in FSD_KEYWORDS)
        matched_keywords = [kw for kw in FSD_KEYWORDS if kw in description]
        if has_fsd_text:
            print(f"   → TEXT MATCH on {url} → keywords: {matched_keywords}")

        has_fsd_screen = False
        for img in soup.find_all('img'):
            img_url = (img.get('src') or img.get('data-src') or img.get('data-lazy') or 
                       img.get('data-original') or img.get('data-srcset') or img.get('srcset'))
            if img_url and any(ext in (img_url.lower() if isinstance(img_url, str) else "") for ext in ('.jpg', '.png', '.jpeg', '.webp')):
                if not img_url.startswith('http'):
                    continue
                try:
                    img_resp = requests.get(img_url, headers=headers, timeout=10)
                    img_data = Image.open(io.BytesIO(img_resp.content))
                    ocr_text = pytesseract.image_to_string(img_data).lower()
                    if any(kw in ocr_text for kw in FSD_KEYWORDS):
                        has_fsd_screen = True
                        print(f"   → OCR MATCH on image {img_url[:80]}... → found FSD")
                        break
                    else:
                        print(f"   → OCR ran but no FSD keywords found in image")
                except Exception:
                    continue
        return {'has_fsd_text': has_fsd_text, 'has_fsd_screen': has_fsd_screen}
    except Exception as e:
        print(f"⚠️ Error on detail page {url}: {e}")
        return {'has_fsd_text': False, 'has_fsd_screen': False}

# ====================== MAIN RUN ======================
current_vins_this_run = set()
new_alerts = []
sold_alerts = []

print(f"🚀 Starting FSD Model Y scan at {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")

for dealer in DEALERS:
    print(f"\nScanning {dealer['name']}...")
    listings = scrape_list_page(dealer)
    for listing in listings:
        vin = listing['vin']
        current_vins_this_run.add(vin)
        current_price_num = parse_price(listing['price'])
        detail = scrape_detail(listing['detail_url'])
        is_fsd_hit = detail['has_fsd_text'] or detail['has_fsd_screen']

        if vin in seen:
            # price drop logic (same as before)
            ...
            continue

        if is_fsd_hit:
            # alert logic (same as before)
            ...
            new_alerts.append(alert_body)
            seen[vin] = {"price": current_price_num, "last_seen": datetime.now().isoformat(), "dealer": dealer["name"]}

# sold detection (unchanged)
...

# email + save (unchanged)
if all_alerts:
    ...
else:
    print("No new hits, price drops, or sold vehicles this run.")

with open(SEEN_FILE, 'w') as f:
    json.dump(seen, f, indent=2)

print(f"✅ Run complete — {len(new_alerts)} new/price alerts + {len(sold_alerts)} sold alerts")
