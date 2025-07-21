from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str

@app.post("/scrape")
def scrape(request: ScrapeRequest):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(request.url, timeout=60000)
        page.wait_for_load_state("networkidle")

        title = page.title()
        try:
            price = page.query_selector("#prcIsum, #mm-saleDscPrc").inner_text()
        except:
            price = "Unknown Price"
        try:
            image = page.query_selector("#icImg").get_attribute("src")
        except:
            image = None

        browser.close()

        return {
            "title": title,
            "price": price,
            "image": image,
            "mileage": None,
            "location": None
        }
