import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# ====================== YOUR SETTINGS ======================
ZIP_CODE = "93453"
USER_COORDS = (35.6, -120.7)  # Atascadero, CA area
EMAIL_TO = os.getenv("EMAIL_TO", "amargaritan@gmail.com")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

FSD_KEYWORDS = [
    "full self-driving", "fsd", "included package", "full self drive",
    "included software", "hw4", "transferable", "purchased fsd",
    "full self-driving capability", "autopilot hw4", "hw 4", "hardware 4"
]

SEEN_FILE = "seen_listings.json"

# Load previously seen VINs
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE) as f:
        seen = json.load(f)
else:
    seen = []

geolocator = Nominatim(user_agent="tesla_fsd_monitor_atascadero")

def send_email(subject, body):
    if not EMAIL_FROM or not EMAIL_PASSWORD:
        print("WARNING: Email credentials (EMAIL_FROM / EMAIL_PASSWORD) not set in secrets. Skipping email.")
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        print(f"✅ Email sent: {subject}")
    except Exception as e:
        print(f"❌ ERROR sending email: {e}")

# ====================== YOUR 20 DEALERS ======================
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
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        potential_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if re.search(dealer["detail_pattern"], href, re.I):
                full_url = href if href.startswith('http') else f"https://{response.url.split('/')[2]}{href if href.startswith('/') else '/' + href}"
                card_text = (a.parent.get_text(strip=True) if a.parent else a.get_text(strip=True))[:500]
                price = next((t for t in re.findall(r'\$\d{1,3}(?:,\d{3})*', card_text)), 'Unknown')
                miles = next((t for t in re.findall(r'\d{1,3}(?:,\d{3})* mi', card_text, re.I)), 'Unknown')
                vin_match = re.search(r'[A-HJ-NPR-Z0-9]{17}', card_text)
                vin = vin_match.group(0) if vin_match else full_url.split('/')[-1].upper()[:17]
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
        print(f"Error scraping list page {dealer['name']}: {e}")
        return []

def scrape_detail(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        description = response.text.lower()
        has_fsd = any(kw in description for kw in FSD_KEYWORDS)
        return {'has_fsd': has_fsd}
    except Exception as e:
        print(f"Error scraping detail page {url}: {e}")
        return {'has_fsd': False}

# ====================== MAIN RUN ======================
new_alerts = []
print(f"🚀 Starting FSD Model Y scan at {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")

for dealer in DEALERS:
    print(f"Scanning {dealer['name']} ...")
    listings = scrape_list_page(dealer)
    for listing in listings:
        vin = listing['vin']
        if vin in seen:
            continue
        detail = scrape_detail(listing['detail_url'])
        if detail['has_fsd']:
            distance = "National"
            try:
                location = geolocator.geocode(dealer["name"] + ", USA", timeout=10)
                if location:
                    dist = geodesic(USER_COORDS, (location.latitude, location.longitude)).miles
                    distance = f"{dist:.0f} miles"
            except (GeocoderTimedOut, GeocoderServiceError, Exception):
                pass

            alert_body = f"""
            <h2>🚀 New FSD-Loaded Model Y Found!</h2>
            <p><strong>Dealer:</strong> {listing['dealer']}</p>
            <p><strong>Title:</strong> {listing['title']}</p>
            <p><strong>Price:</strong> {listing['price']} | <strong>Miles:</strong> {listing['miles']}</p>
            <p><strong>Distance:</strong> {distance}</p>
            <p><strong>FSD detected in listing text</strong></p>
            <p><a href="{listing['detail_url']}">View Full Listing →</a></p>
            <p><small>Checked: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</small></p>
            """
            new_alerts.append(alert_body)
            seen.append(vin)
            print(f"✅ New match: {listing['title']} at {listing['dealer']}")

if new_alerts:
    send_email(f"🚀 {len(new_alerts)} New FSD Model Y Match(es) Found!", "\n\n".join(new_alerts))
else:
    print("No new FSD matches found this run.")

# Save updated seen list
with open(SEEN_FILE, 'w') as f:
    json.dump(seen, f)

print(f"✅ Run complete - {len(new_alerts)} new alerts")
