from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright

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

            # Scroll to bottom to trigger image loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # Get title
            title = page.title()

            # Try multiple price selectors
            price_selectors = ["#prcIsum", "#mm-saleDscPrc", ".x-price-approx__price", ".x-price-approx__value"]
            price = "Unknown Price"
            for selector in price_selectors:
                el = page.query_selector(selector)
                if el:
                    price = el.inner_text()
                    break

            # Try image selector
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
