import requests
from bs4 import BeautifulSoup
import time
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
import re

# ====================== YOUR SETTINGS ======================
ZIP_CODE = "93453"
USER_COORDS = (35.6, -120.7)
EMAIL_TO = os.getenv("EMAIL_TO", "amargaritan@gmail.com")
FSD_KEYWORDS = [
    "full self-driving", "fsd", "included package", "full self drive",
    "included software", "hw4", "transferable", "purchased fsd",
    "full self-driving capability", "autopilot hw4"
]

SEEN_FILE = "seen_listings.json"

if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE) as f:
        seen = json.load(f)
else:
    seen = {}

geolocator = Nominatim(user_agent="tesla_fsd_monitor")

def parse_price(price_str):
    if not price_str or price_str == "Unknown":
        return None
    try:
        return float(re.sub(r'[^0-9.]', '', price_str))
    except:
        return None

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = os.getenv("EMAIL_FROM")
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_PASSWORD"))
        server.sendmail(os.getenv("EMAIL_FROM"), EMAIL_TO, msg.as_string())
        server.quit()
        print("✅ Email sent successfully")
    except Exception as e:
        print(f"❌ Email send failed: {e}")

# ====================== ALL 20 DEALERS ======================
DEALERS = [
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
]

def scrape_list_page(dealer):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(dealer["url"], headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        potential_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if re.search(dealer["detail_pattern"], href, re.I):
                full_url = href if href.startswith('http') else 'https://' + response.url.split('/')[2] + ('' if href.startswith('/') else '/') + href
                card_text = a.parent.get_text(strip=True) if a.parent else ""
                price = next((t for t in re.findall(r'\$\d{1,3}(?:,\d{3})*', card_text)), 'Unknown')
                miles = next((t for t in re.findall(r'\d{1,3}(?:,\d{3})* mi', card_text, re.I)), 'Unknown')
                vin_match = re.search(r'[A-HJ-NPR-Z0-9]{17}', card_text)
                vin = vin_match.group(0) if vin_match else full_url.split('/')[-1]
                title = a.get_text(strip=True)[:150] or "Tesla Model Y"
                potential_links.append({
                    'title': title,
                    'price': price,
                    'miles': miles,
                    'vin': vin,
                    'detail_url': full_url,
                    'dealer': dealer["name"]
                })
        return list({v['detail_url']: v for v in potential_links}.values())
    except Exception as e:
        print(f"⚠️ Error scraping {dealer['name']}: {e}")
        return []

def scrape_detail(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        description = soup.get_text().lower()
        has_fsd_text = any(kw in description for kw in FSD_KEYWORDS)
        has_fsd_screen = False
        for img in soup.find_all('img'):
            img_url = img.get('src') or img.get('data-src') or img.get('data-lazy') or img.get('data-original')
            if img_url and img_url.startswith('http') and any(ext in img_url.lower() for ext in ('.jpg', '.png', '.jpeg')):
                try:
                    img_resp = requests.get(img_url, headers=headers, timeout=8)
                    img_data = Image.open(io.BytesIO(img_resp.content))
                    ocr_text = pytesseract.image_to_string(img_data).lower()
                    if any(kw in ocr_text for kw in FSD_KEYWORDS):
                        has_fsd_screen = True
                        break
                except:
                    continue
        return {'has_fsd_text': has_fsd_text, 'has_fsd_screen': has_fsd_screen}
    except Exception as e:
        print(f"⚠️ Error on detail page {url}: {e}")
        return {'has_fsd_text': False, 'has_fsd_screen': False}

# ====================== MAIN RUN ======================
current_vins_this_run = set()
new_alerts = []
sold_alerts = []

for dealer in DEALERS:
    listings = scrape_list_page(dealer)
    for listing in listings:
        vin = listing['vin']
        current_vins_this_run.add(vin)
        current_price_num = parse_price(listing['price'])
        detail = scrape_detail(listing['detail_url'])
        is_fsd_hit = detail['has_fsd_text'] or detail['has_fsd_screen']

        if vin in seen:
            old_price_num = seen[vin].get("price")
            if is_fsd_hit and current_price_num and old_price_num and current_price_num < old_price_num:
                distance = "National"
                try:
                    location = geolocator.geocode(dealer["name"] + ", USA")
                    if location:
                        dist = geodesic(USER_COORDS, (location.latitude, location.longitude)).miles
                        distance = f"{dist:.0f} miles from you"
                except:
                    pass
                alert_body = f"""
                <h2>💰 Price Drop on FSD-Loaded Model Y!</h2>
                <p><strong>Dealer:</strong> {listing['dealer']}</p>
                <p><strong>Title:</strong> {listing['title']}</p>
                <p><strong>Old Price:</strong> ${old_price_num:,.0f} → <strong>New Price:</strong> ${current_price_num:,.0f}</p>
                <p><strong>Miles:</strong> {listing['miles']} | <strong>Distance:</strong> {distance}</p>
                <p><strong>FSD Proof:</strong> Text: {'✓' if detail['has_fsd_text'] else '✗'} | Screen OCR: {'✓' if detail['has_fsd_screen'] else '✗'}</p>
                <p><a href="{listing['detail_url']}">View Listing →</a></p>
                """
                new_alerts.append(alert_body)
            seen[vin] = {"price": current_price_num or old_price_num, "last_seen": datetime.now().isoformat(), "dealer": dealer["name"]}
            continue

        if is_fsd_hit:
            distance = "National"
            try:
                location = geolocator.geocode(dealer["name"] + ", USA")
                if location:
                    dist = geodesic(USER_COORDS, (location.latitude, location.longitude)).miles
                    distance = f"{dist:.0f} miles from you"
            except:
                pass
            alert_body = f"""
            <h2>🚀 New FSD-Loaded Model Y Found!</h2>
            <p><strong>Dealer:</strong> {listing['dealer']}</p>
            <p><strong>Title:</strong> {listing['title']}</p>
            <p><strong>Price:</strong> {listing['price']} | <strong>Miles:</strong> {listing['miles']}</p>
            <p><strong>Distance:</strong> {distance}</p>
            <p><strong>FSD Proof:</strong> Text: {'✓' if detail['has_fsd_text'] else '✗'} | Screen OCR: {'✓' if detail['has_fsd_screen'] else '✗'}</p>
            <p><a href="{listing['detail_url']}">View Listing & Photos →</a></p>
            """
            new_alerts.append(alert_body)
            seen[vin] = {"price": current_price_num, "last_seen": datetime.now().isoformat(), "dealer": dealer["name"]}

# Detect likely sold vehicles
for vin in list(seen.keys()):
    if vin not in current_vins_this_run:
        last_price = seen[vin].get("price")
        dealer_name = seen[vin].get("dealer", "Unknown Dealer")
        alert_body = f"""
        <h2>🚗 Likely Sold / Removed</h2>
        <p><strong>Dealer:</strong> {dealer_name}</p>
        <p><strong>VIN:</strong> {vin}</p>
        <p><strong>Likely sale price:</strong> ${last_price:,.0f} (last known price)</p>
        <p><small>This vehicle was a confirmed FSD hit but no longer appears.</small></p>
        """
        sold_alerts.append(alert_body)
        del seen[vin]

all_alerts = new_alerts + sold_alerts
if all_alerts:
    subject = f"🚀 {len(new_alerts)} New + {len(sold_alerts)} Sold/Price-Change FSD Model Y Update(s)"
    body = "\n\n".join(all_alerts)
    send_email(subject, body)
else:
    print("No new hits, price drops, or sold vehicles this run")

with open(SEEN_FILE, 'w') as f:
    json.dump(seen, f, indent=2)

print(f"Run complete — {len(new_alerts)} new/price alerts + {len(sold_alerts)} sold alerts")
