from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import time

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
            time.sleep(2)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            title = page.title()

            # Price scraping
            price_selectors = [
                "#prcIsum", "#mm-saleDscPrc", ".x-price-approx__price", ".x-price-approx__value",
                ".display-price", ".x-bin-price", "[itemprop='price']"
            ]
            price = "Unknown Price"
            for selector in price_selectors:
                el = page.query_selector(selector)
                if el:
                    price = el.inner_text()
                    break

            # Image
            image = None
            img = page.query_selector("#icImg") or page.query_selector("img[src*='ebayimg']")
            if img:
                image = img.get_attribute("src")

            # Item specifics scraping from eBay's modern layout
            specifics = {}
            fields_we_want = [
                "Year", "Exterior Colour", "Interior Colour", "Manufacturer",
                "Model", "Engine Size", "Mileage", "Fuel Type"
            ]

            page.wait_for_selector(".ux-layout-section-evo__row", timeout=15000)
            rows = page.query_selector_all(".ux-layout-section-evo__row")
            for row in rows:
                label_el = row.query_selector(".ux-labels-values__labels .ux-textspans")
                value_el = row.query_selector(".ux-labels-values__values .ux-textspans")
                if label_el and value_el:
                    label = label_el.inner_text().strip().replace(":", "")
                    value = value_el.inner_text().strip()
                    if label in fields_we_want:
                        specifics[label.lower().replace(" ", "_")] = value

            browser.close()

            return {
                "title": title,
                "price": price,
                "image": image,
                **specifics
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



