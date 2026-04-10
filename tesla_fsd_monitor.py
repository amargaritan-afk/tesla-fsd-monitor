import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import re

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
    "capability included", "software included", "included full self-driving",
    # Specific for Redline / DriveCoolCars
    "full self drive hw4", "full self drive", "autopilot hw4"
]

SEEN_FILE = "seen_listings.json"

if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE) as f:
        seen = json.load(f)
else:
    seen = {}

geolocator = Nominatim(user_agent="tesla_fsd_monitor_atascadero")

def parse_price(price_str):
    if not price_str or price_str == "Unknown":
        return None
    try:
        return float(re.sub(r'[^0-9.]', '', price_str))
    except:
        return None

def send_email(subject, body):
    if not os.getenv("EMAIL_FROM") or not os.getenv("EMAIL_PASSWORD"):
        print("⚠️ Email credentials not set. Skipping send.")
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = os.getenv("EMAIL_FROM")
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_PASSWORD"))
        server.sendmail(os.getenv("EMAIL_FROM"), EMAIL_TO, msg.as_string())
        server.quit()
        print("✅ Email sent successfully")
    except Exception as e:
        print(f"❌ Email send failed: {e}")

# ====================== DEALERS ======================
DEALERS = [
    {"name": "DriveCoolCars", "url": "https://www.drivecoolcars.com/newandusedcars?Year=2024&MakeName=Tesla&ModelName=Model%20Y&ClearAll=1", "detail_pattern": r"/vdp/"},
    # Add the rest of your 19 dealers + AutoTempest here (copy from previous full script)
    # For brevity I'm showing only DriveCoolCars — paste all others exactly as before
    {"name": "AutoTempest", "url": "https://www.autotempest.com/results?drive=awd&localization=country&make=tesla&maxmiles=55000&maxprice=55000&minmiles=0&minprice=27000&minyear=2023&model=modely&saletype=classified&title=clean&zip=93453", "detail_pattern": r"/vehicle/|/details/|carvana.com/vehicle/|cars.com/vehicledetail/"},
    # ... paste the other 19 dealers ...
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
        print(f"   → {dealer['name']}: {len(potential_links)} listings found on list page")
        return list({v['detail_url']: v for v in potential_links}.values())
    except Exception as e:
        print(f"⚠️ Error scraping list page {dealer['name']}: {e}")
        return []

def scrape_detail(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        description = response.text.lower()
        has_fsd = any(kw in description for kw in FSD_KEYWORDS)
        if has_fsd:
            matched = [kw for kw in FSD_KEYWORDS if kw in description]
            print(f"   → ✅ TEXT MATCH on {url} | Keywords: {matched}")
        elif "drivecoolcars" in url.lower():
            print(f"   → DriveCoolCars detail checked — no strong FSD keywords found: {url}")
        return {'has_fsd': has_fsd}
    except Exception as e:
        print(f"⚠️ Error on detail page {url}: {e}")
        return {'has_fsd': False}

# ====================== MAIN RUN (same as previous text-only version) ======================
# ... paste the full main run logic from the previous OCR-free script I gave you (current_vins_this_run, new_alerts, sold_alerts, price drop logic, email, save seen file, final print) ...

print(f"✅ Run complete — {len(new_alerts)} new/price alerts + {len(sold_alerts)} sold alerts")
