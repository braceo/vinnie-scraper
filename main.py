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
            page.goto(request.url, timeout=60000)
            page.wait_for_load_state("networkidle")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

            title = page.title().strip()

            # Price scraping
            price_selectors = [
                "#prcIsum", "#mm-saleDscPrc", ".x-price-approx__price", ".x-price-approx__value",
                ".display-price", ".x-bin-price", "[itemprop='price']"
            ]
            price_raw = "Unknown"
            for selector in price_selectors:
                el = page.query_selector(selector)
                if el:
                    price_raw = el.inner_text().strip()
                    break

            # Normalize price to just number
            price = "Unknown"
            match = re.search(r"£\s?([\d,]+(?:\.\d{2})?)", price_raw)
            if match:
                price = f"£{match.group(1)}"

            # Image
            image = None
            img = page.query_selector("#icImg") or page.query_selector("img[src*='ebayimg']")
            if img:
                image = img.get_attribute("src")

            # Initialize specifics with fallback values
            specifics = {
                "mileage": "Unknown",
                "exterior_colour": "Unknown",
                "interior_colour": "Unknown",
                "manufacturer": "Unknown",
                "model": "Unknown",
                "fuel_type": "Unknown",
                "engine_size": "Unknown",
                "year": "Unknown",
                "body_type": "Unknown",
                "transmission": "Unknown"
            }

            # Scrape item specifics
            rows = page.query_selector_all("div.ux-layout-section-evo__row")

            for row in rows:
                label_el = row.query_selector(".ux-labels-values__labels")
                value_el = row.query_selector(".ux-labels-values__values")

                if label_el and value_el:
                    label = label_el.inner_text().strip().replace(":", "").lower()
                    value = value_el.inner_text().strip()

                    key_map = {
                        "mileage": "mileage",
                        "exterior colour": "exterior_colour",
                        "interior colour": "interior_colour",
                        "manufacturer": "manufacturer",
                        "model": "model",
                        "fuel type": "fuel_type",
                        "engine size": "engine_size",
                        "year": "year",
                        "body type": "body_type",
                        "transmission": "transmission"
                    }

                    if label in key_map:
                        clean_value = re.sub(r"\s+", " ", value)
                        specifics[key_map[label]] = clean_value

            # Clean mileage
            if specifics["mileage"] != "Unknown":
                mileage_digits = re.search(r"([\d,]+)", specifics["mileage"])
                if mileage_digits:
                    specifics["mileage"] = mileage_digits.group(1).replace(",", "")
                else:
                    specifics["mileage"] = "Unknown"

            browser.close()

            return {
                "title": title,
                "price": price,
                "image": image,
                **specifics
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



