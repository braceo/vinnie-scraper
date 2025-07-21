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
            page = browser.new_page()
            page.goto(request.url, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)  # Wait a bit more for price to render

            # Scroll to trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            # Title
            title = page.title()

            # Price selectors (expanded list)
            price_selectors = [
                "#prcIsum",                # Standard
                "#mm-saleDscPrc",          # Discounted
                ".x-price-approx__price",  # Alternative layout
                ".x-price-approx__value",
                ".display-price",          # Auction layouts
                ".x-bin-price",            # Buy It Now boxed style
                "[itemprop='price']"       # Semantic HTML
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

            browser.close()

            return {
                "title": title,
                "price": price,
                "image": image,
                "mileage": None,
                "location": None
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
