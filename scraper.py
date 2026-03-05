import asyncio
import logging
import json
import os
from dotenv import load_dotenv
from core.requester import Requester
from core.login import EanyLogin

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

JSON_FILE = "products.json"
STATE_FILE = "category_state.json"
CONCURRENT_REQUESTS = 50
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

CATEGORIES = [
    "https://backend.eany.io/api/v1/products?category=537&page={}",
    "https://backend.eany.io/api/v1/products?category=111&page={}",
    "https://backend.eany.io/api/v1/products?category=141&page={}",
    "https://backend.eany.io/api/v1/products?category=222&page={}",
    "https://backend.eany.io/api/v1/products?category=632&page={}",
    "https://backend.eany.io/api/v1/products?category=469&page={}",
    "https://backend.eany.io/api/v1/products?category=536&page={}",
    "https://backend.eany.io/api/v1/products?category=922&page={}",
    "https://backend.eany.io/api/v1/products?category=2092&page={}",
    "https://backend.eany.io/api/v1/products?category=988&page={}",
    "https://backend.eany.io/api/v1/products?category=1239&page={}",
    "https://backend.eany.io/api/v1/products?category=888&page={}"
]

def load_state():
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w") as f:
            json.dump({"current_index": 0}, f)
        return 0
    with open(STATE_FILE, "r") as f:
        data = json.load(f)
        return data.get("current_index", 0)

def save_state(index):
    with open(STATE_FILE, "w") as f:
        json.dump({"current_index": index}, f)

async def scrape_page(session, semaphore, url, page, existing_keys):
    async with semaphore:
        try:
            response = await session.fetch_get(url)
        except Exception as e:
            logger.error(f"Request failed page {page}: {e}")
            return [], None

        if not response or response.status_code != 200:
            logger.warning(f"Page {page} status {getattr(response, 'status_code', None)}")
            return [], None

        resp = json.loads(response.text)
        data = resp["data"]
        last_page = resp.get("pagination", {}).get("last", None)

        page_products = []
        skipped_no_name = 0
        skipped_invalid_id = 0
        skipped_dup = 0

        for i in data:
            name = (i.get("name") or "").strip()
            gtin = (i.get("ean") or "").strip()
            asin = (i.get("asin") or "").strip()
            stocks = i.get("stocks") or []
            price = stocks[0]["unit_price_net"] if stocks else None

            if not name:
                skipped_no_name += 1
                continue
            if not (gtin.isdigit() and len(gtin) == 13):
                gtin = None
            if len(asin) != 10:
                asin = None
            if not gtin or not asin:
                skipped_invalid_id += 1
                continue

            unique_key = f"{gtin}_{asin}"
            if unique_key in existing_keys:
                skipped_dup += 1
                continue

            existing_keys.add(unique_key)
            product_link = f"https://eany.io/product/{gtin}"

            page_products.append({
                "product_name": name,
                "product_gtin": gtin,
                "supplier_price": price,
                "product_link": product_link,
                "asin": asin
            })

        logger.info(
            f"Page {page} new {len(page_products)} | "
            f"no_name {skipped_no_name} | "
            f"invalid_id {skipped_invalid_id} | "
            f"dup {skipped_dup}"
        )
        return page_products, last_page

async def eany_scraper():
    product_data = []
    existing_keys = set()
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    if not EMAIL or not PASSWORD:
        raise ValueError("Missing EMAIL or PASSWORD in .env")

    login = EanyLogin(email=EMAIL, password=PASSWORD, headless=False)
    cookies = await login.login()
    if not cookies:
        raise RuntimeError("Login failed")

    async with Requester(proxy=os.getenv("PROXY"), cookie=cookies) as session:
        data = await session.fetch_get("https://eany.io/api/auth/session")
        auth_token = json.loads(data.text)["token"]

    current_index = load_state()
    category_url_template = CATEGORIES[current_index]

    async with Requester(proxy=os.getenv("PROXY"), token=auth_token) as session:
        first_url = category_url_template.format(1)
        first_page_data, last_page = await scrape_page(session, semaphore, first_url, 1, existing_keys)
        product_data.extend(first_page_data)

        tasks = []
        for page in range(2, last_page + 1):
            url = category_url_template.format(page)
            tasks.append(scrape_page(session, semaphore, url, page, existing_keys))

        results = await asyncio.gather(*tasks)
        for r, _ in results:
            product_data.extend(r)

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(product_data, f, ensure_ascii=False, indent=4)

    next_index = (current_index + 1) % len(CATEGORIES)
    save_state(next_index)

if __name__ == "__main__":
    asyncio.run(eany_scraper())