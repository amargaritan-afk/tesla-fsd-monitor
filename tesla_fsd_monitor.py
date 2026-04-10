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

# ====================== SETTINGS ======================
EMAIL_TO = os.getenv("EMAIL_TO", "amargaritan@gmail.com")
FSD_KEYWORDS = [
    "full self-driving", "fsd", "included package", "full self drive",
    "included software", "hw4", "hw 4", "hardware 4",
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
    email_from = os.getenv("EMAIL_FROM")
    email_pass = os.getenv("EMAIL_PASSWORD")
    if not email_from or not email_pass:
        print("⚠️ Email credentials missing.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_from, email_pass)
        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False

# ====================== DEALERS ======================
DEALERS = [ ... ]   # Keep your full list of 21 dealers here (same as before)

# (scrape_list_page and scrape_detail functions stay the same as your current version)

# ====================== MAIN RUN (with deduplication) ======================
current_vins_this_run = set()
new_alerts = []
seen_this_run = set()

print(f"🚀 Starting scan at {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")

for dealer in DEALERS:
    print(f"\nScanning {dealer['name']}...")
    listings = scrape_list_page(dealer)
    for listing in listings:
        vin = listing['vin']
        if vin in seen_this_run:
            continue
        seen_this_run.add(vin)
        current_vins_this_run.add(vin)

        detail = scrape_detail(listing['detail_url'])
        if not detail['has_fsd']:
            continue

        if vin in seen:
            # price drop logic (simplified)
            seen[vin] = {"price": parse_price(listing['price']), "last_seen": datetime.now().isoformat(), "dealer": dealer["name"]}
            continue

        # New match
        distance = "National"
        try:
            loc = geolocator.geocode(dealer["name"] + ", USA", timeout=8)
            if loc:
                dist = geodesic(USER_COORDS, (loc.latitude, loc.longitude)).miles
                distance = f"{dist:.0f} miles"
        except:
            pass

        alert_body = f"""
        <h2>🚀 New FSD/HW4 Model Y Found!</h2>
        <p><strong>Dealer:</strong> {listing['dealer']}</p>
        <p><strong>Title:</strong> {listing['title']}</p>
        <p><strong>Price:</strong> {listing['price']} | <strong>Miles:</strong> {listing['miles']}</p>
        <p><strong>Distance:</strong> {distance}</p>
        <p><a href="{listing['detail_url']}">View Listing →</a></p>
        """
        new_alerts.append(alert_body)
        seen[vin] = {"price": parse_price(listing['price']), "last_seen": datetime.now().isoformat(), "dealer": dealer["name"]}
        print(f"✅ New match: {listing['title']} at {listing['dealer']}")

# Save seen
with open(SEEN_FILE, 'w') as f:
    json.dump(seen, f, indent=2)

if new_alerts:
    subject = f"🚀 {len(new_alerts)} New FSD/HW4 Model Y Match(es) Found!"
    body = "\n\n".join(new_alerts)
    send_email(subject, body)
else:
    print("No new matches this run.")

print(f"✅ Run complete — {len(new_alerts)} new alerts")
