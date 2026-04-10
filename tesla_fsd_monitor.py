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
