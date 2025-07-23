from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import time
import re

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str

@app.post("/scrape")
def scrape(request: ScrapeRequest):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "DNT": "1",
                    "Upgrade-Insecure-Requests": "1"
                }
            )

            # Load page
            page.goto(request.url, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            # Basic fields
            title = page.title().strip()

            # Price
            price_raw = "Unknown"
            for sel in ["#prcIsum", "#mm-saleDscPrc", ".x-price-approx__price",
                        ".x-price-approx__value", ".display-price", ".x-bin-price",
                        "[itemprop='price']"]:
                el = page.query_selector(sel)
                if el:
                    price_raw = el.inner_text().strip()
                    break
            m = re.search(r"£\s?([\d,]+(?:\.\d{2})?)", price_raw)
            price = f"£{m.group(1)}" if m else "Unknown"

            # Image
            image = None
            img = page.query_selector("#icImg") or page.query_selector("img[src*='ebayimg']")
            if img:
                image = img.get_attribute("src")

            # Initialize all specifics with fallback
            specifics = {
                "year": "Unknown",
                "manufacturer": "Unknown",
                "model": "Unknown",
                "engine_size": "Unknown",
                "fuel_type": "Unknown",
                "body_type": "Unknown",
                "transmission": "Unknown",
                "mileage": "Unknown",
                "exterior_colour": "Unknown",
                "interior_colour": "Unknown"
            }

            # 1) Modern evo rows (divs)
            for row in page.query_selector_all("div.ux-layout-section-evo__row"):
                lab = row.query_selector("div.ux-labels-values__labels span.ux-textspans")
                val = row.query_selector("div.ux-labels-values__values span.ux-textspans")
                if not lab or not val:
                    continue
                label = lab.inner_text().strip().rstrip(":").lower()
                value = val.inner_text().strip()
                key_map = {
                    "year": "year",
                    "manufacturer": "manufacturer",
                    "model": "model",
                    "engine size": "engine_size",
                    "fuel type": "fuel_type",
                    "body type": "body_type",
                    "transmission": "transmission",
                    "mileage": "mileage",
                    "exterior colour": "exterior_colour",
                    "interior colour": "interior_colour"
                }
                if label in key_map:
                    specifics[key_map[label]] = value

            # 2) <dl> lists fallback
            for dl in page.query_selector_all("dl.ux-labels-values"):
                lab = dl.query_selector("dt.ux-labels-values__labels span.ux-textspans")
                val = dl.query_selector("dd.ux-labels-values__values span.ux-textspans")
                if not lab or not val:
                    continue
                label = lab.inner_text().strip().rstrip(":").lower()
                value = val.inner_text().strip()
                key_map = {
                    "year": "year",
                    "manufacturer": "manufacturer",
                    "model": "model",
                    "engine size": "engine_size",
                    "fuel type": "fuel_type",
                    "body type": "body_type",
                    "transmission": "transmission",
                    "mileage": "mileage",
                    "exterior colour": "exterior_colour",
                    "interior colour": "interior_colour"
                }
                if label in key_map and specifics[key_map[label]] == "Unknown":
                    specifics[key_map[label]] = value

            # 3) <ul><li> legacy fallback
            for li in page.query_selector_all("ul.ux-labels-values__content li"):
                text = li.inner_text().strip().split(":", 1)
                if len(text) != 2:
                    continue
                label, value = text[0].lower(), text[1].strip()
                key_map = {
                    "year": "year",
                    "manufacturer": "manufacturer",
                    "model": "model",
                    "engine size": "engine_size",
                    "fuel type": "fuel_type",
                    "body type": "body_type",
                    "transmission": "transmission",
                    "mileage": "mileage",
                    "exterior colour": "exterior_colour",
                    "interior colour": "interior_colour"
                }
                if label in key_map and specifics[key_map[label]] == "Unknown":
                    specifics[key_map[label]] = value

            # Normalize mileage digits
            if specifics["mileage"] != "Unknown":
                m2 = re.search(r"([\d,]+)", specifics["mileage"])
                specifics["mileage"] = m2.group(1).replace(",", "") if m2 else "Unknown"

            browser.close()

            return {
                "title": title,
                "price": price,
                "image": image,
                **specifics
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



