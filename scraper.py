import json
import os
import re
from difflib import SequenceMatcher
from urllib.parse import quote

from playwright.sync_api import sync_playwright


# =========================================================
# CONFIGURATION
# =========================================================

HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

MAX_PRODUCTS = 5

PAGE_TIMEOUT = 30000
WAIT_TIME = 6000

PLATFORMS = [
    "Blinkit",
    "Zepto",
    "Instamart",
    "BigBasket"
]

LOCATIONS = {
    "mumbai": {
        "name": "Mumbai",
        "pincode": "400001",
        "lat": 19.0760,
        "lng": 72.8777
    },
    "delhi": {
        "name": "Delhi / NCR",
        "pincode": "110001",
        "lat": 28.6139,
        "lng": 77.2090
    },
    "bengaluru": {
        "name": "Bengaluru",
        "pincode": "560001",
        "lat": 12.9716,
        "lng": 77.5946
    },
    "gurgaon": {
        "name": "Gurgaon",
        "pincode": "122001",
        "lat": 28.4595,
        "lng": 77.0266
    },
    "hyderabad": {
        "name": "Hyderabad",
        "pincode": "500001",
        "lat": 17.3850,
        "lng": 78.4867
    },
    "kolkata": {
        "name": "Kolkata",
        "pincode": "700001",
        "lat": 22.5726,
        "lng": 88.3639
    },
    "chennai": {
        "name": "Chennai",
        "pincode": "600001",
        "lat": 13.0827,
        "lng": 80.2707
    },
    "pune": {
        "name": "Pune",
        "pincode": "411001",
        "lat": 18.5204,
        "lng": 73.8567
    }
}


# =========================================================
# PRICE EXTRACTION
# =========================================================

def extract_price(text):

    if not text:
        return None

    patterns = [
        r"₹\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)",
        r"(?:Rs\.?|INR)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                price = float(
                    match.group(1).replace(",", "")
                )

                if 0 < price < 100000:
                    return price

            except Exception:
                pass

    return None


# =========================================================
# CLEAN PRODUCT NAME
# =========================================================

def clean_name(name):

    if not name:
        return ""

    name = name.lower()

    name = re.sub(
        r"\b(?:₹|rs\.?|inr)\s*\d+(?:\.\d+)?\b",
        " ",
        name
    )

    name = re.sub(
        r"[^a-z0-9]+",
        " ",
        name
    )

    return " ".join(name.split())


# =========================================================
# PACK SIZE
# =========================================================

def extract_pack_size(name):

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(kg|g|mg|ml|l)\b",
        clean_name(name)
    )

    if match:
        return (
            f"{match.group(1)}"
            f"{match.group(2)}"
        )

    return None


# =========================================================
# PRODUCT MATCHING
# =========================================================

def product_match_score(first, second):

    first_clean = clean_name(first)
    second_clean = clean_name(second)

    if not first_clean or not second_clean:
        return 0

    first_size = extract_pack_size(first)
    second_size = extract_pack_size(second)

    # Do not match different pack sizes
    if (
        first_size
        and second_size
        and first_size != second_size
    ):
        return 0

    sequence_score = SequenceMatcher(
        None,
        first_clean,
        second_clean
    ).ratio()

    first_tokens = set(
        first_clean.split()
    )

    second_tokens = set(
        second_clean.split()
    )

    union = first_tokens | second_tokens

    overlap_score = (
        len(first_tokens & second_tokens)
        / len(union)
        if union
        else 0
    )

    return (
        sequence_score * 0.55
        + overlap_score * 0.45
    )


# =========================================================
# RELEVANCE FILTER
# =========================================================

def is_relevant_product(query, name):

    if not query or not name:
        return True

    clean_q = clean_name(query)
    clean_n = clean_name(name)

    if not clean_q or not clean_n:
        return True

    if clean_q in clean_n:
        return True

    q_tokens = [t for t in clean_q.split() if len(t) > 2]

    if not q_tokens:
        return True

    return any(
        t in clean_n
        for t in q_tokens
    )


# =========================================================
# ADD PRODUCT
# =========================================================

def add_product(results, name, price, query=None):

    if not name or price is None:
        return

    name = " ".join(name.split())

    if len(name) < 4:
        return

    ignored = [
        "add",
        "buy",
        "cart",
        "wishlist",
        "login",
        "sign in",
        "delivery",
        "select location",
        "shop by category",
        "see all"
    ]

    if name.lower() in ignored:
        return

    if query and not is_relevant_product(query, name):
        return

    normalized = clean_name(name)

    if not normalized:
        return

    for product in results:

        if clean_name(
            product["name"]
        ) == normalized:
            return

    results.append({
        "name": name[:150],
        "price": price
    })


# =========================================================
# SAFE TEXT
# =========================================================

def safe_text(locator, timeout=1500):

    try:

        return locator.inner_text(
            timeout=timeout
        ).strip()

    except Exception:

        return ""


# =========================================================
# SCROLL
# =========================================================

def scroll_page(page):

    try:

        for _ in range(4):

            page.mouse.wheel(
                0,
                1200
            )

            page.wait_for_timeout(
                1200
            )

    except Exception:
        pass


# =========================================================
# BLOCK DETECTION
# =========================================================

def page_is_blocked(page):

    try:

        text = page.locator(
            "body"
        ).inner_text(
            timeout=3000
        ).lower()

    except Exception:

        return False

    blocked_phrases = [

        "request blocked",

        "your request looks automated",

        "access denied",

        "verify you are human",

        "captcha",

        "unusual traffic",

        "temporarily unavailable"

    ]

    for phrase in blocked_phrases:

        if phrase in text:
            return True

    return False


# =========================================================
# GENERIC PRODUCT CARD EXTRACTION
# =========================================================

def generic_dom_extraction(
    page,
    card_selectors,
    name_selectors,
    query=None
):

    results = []

    cards = []

    # -----------------------------------------------------
    # Find product cards
    # -----------------------------------------------------

    for selector in card_selectors:

        try:

            locator = page.locator(
                selector
            )

            count = locator.count()

            if count == 0:
                continue

            print(
                f"Selector: {selector}"
            )

            print(
                f"Cards found: {count}"
            )

            cards = locator.all()

            for card in cards:

                try:

                    text = safe_text(
                        card,
                        2000
                    )

                    if not text:
                        continue

                    price = extract_price(
                        text
                    )

                    if price is None:
                        continue

                    name = ""

                    # Try known name elements
                    for name_sel in name_selectors:

                        try:

                            name_loc = card.locator(
                                name_sel
                            )

                            if name_loc.count() > 0:

                                candidate = safe_text(
                                    name_loc.first
                                )

                                if candidate:

                                    name = candidate

                                    break

                        except Exception:
                            continue

                    # Fallback to text lines
                    if not name:

                        lines = [
                            line.strip()
                            for line in text.splitlines()
                            if line.strip()
                        ]

                        for line in lines:

                            if len(line) < 5:
                                continue

                            if re.search(
                                r"₹|Rs\.?|INR",
                                line,
                                re.IGNORECASE
                            ):
                                continue

                            if re.search(
                                r"add|cart|wishlist|delivery",
                                line,
                                re.IGNORECASE
                            ):
                                continue

                            name = line

                            break

                    add_product(
                        results,
                        name,
                        price,
                        query=query
                    )

                    if len(results) >= MAX_PRODUCTS:
                        break

                except Exception:
                    continue

            if results:
                break

        except Exception:
            continue

    if not results:
        try:
            content = page.content()
            json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', content, re.DOTALL)
            json_blocks += re.findall(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', content, re.DOTALL)
            for block in json_blocks:
                if len(results) >= MAX_PRODUCTS:
                    break
                try:
                    data = json.loads(block)
                    def extract_items(obj):
                        if len(results) >= MAX_PRODUCTS:
                            return
                        if isinstance(obj, dict):
                            n = obj.get("name") or obj.get("title") or obj.get("product_name") or obj.get("sku_name")
                            p = obj.get("price") or obj.get("mrp") or obj.get("offer_price") or obj.get("sp") or obj.get("discounted_price")
                            if isinstance(n, str) and isinstance(p, (int, float)) and 0 < p < 100000:
                                add_product(results, n, float(p), query=query)
                            for val in obj.values():
                                extract_items(val)
                        elif isinstance(obj, list):
                            for item in obj:
                                extract_items(item)
                    extract_items(data)
                except Exception:
                    pass
        except Exception:
            pass

    return results[:MAX_PRODUCTS]


# =========================================================
# BLINKIT
# =========================================================

def scrape_blinkit(page, query):

    print("\nOpening Blinkit:")

    url = (
        "https://blinkit.com/s/?q="
        + quote(query)
    )

    print(url)

    try:

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT
        )

        page.wait_for_timeout(
            WAIT_TIME
        )

        print(
            "[Blinkit] URL:",
            page.url
        )

        if page_is_blocked(page):

            print(
                "[Blinkit] BLOCKED"
            )

            return []

        scroll_page(page)

        selectors = [

            "div[role='button']",

            "[data-testid*='product']",

            "[class*='product']",

            "div.tw-text-300.tw-font-semibold.tw-line-clamp-2"

        ]

        results = generic_dom_extraction(

            page,

            selectors,

            [

                "div.tw-text-300.tw-font-semibold.tw-line-clamp-2",

                "[class*='line-clamp']",

                "[class*='product-name']",

                "[class*='productName']"

            ],

            query=query

        )

        print(
            f"Blinkit -> {len(results)} products"
        )

        return results

    except Exception as e:

        print(
            "[Blinkit] Error:",
            e
        )

        return []


# =========================================================
# ZEPTO
# =========================================================

def scrape_zepto(page, query):

    print("\nOpening Zepto:")

    urls = [

        (
            "https://www.zeptonow.com/"
            "search?query="
            + quote(query)
        ),

        (
            "https://www.zeptonow.com/"
            "search?q="
            + quote(query)
        )

    ]

    for url in urls:

        print(url)

        try:

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=PAGE_TIMEOUT
            )

            page.wait_for_timeout(
                WAIT_TIME
            )

            print(
                "[Zepto] URL:",
                page.url
            )

            if page_is_blocked(page):

                print(
                    "[Zepto] BLOCKED"
                )

                continue

            scroll_page(page)

            selectors = [

                "a[data-testid='product-card']",

                "[data-testid='product-card']",

                "[data-testid*='product-card']",

                "a[href*='/pn/']",

                "[class*='ProductCard']",

                "[class*='product-card']"

            ]

            results = generic_dom_extraction(

                page,

                selectors,

                [

                    "h5",
                    "h4",
                    "h3",

                    "[class*='name']",

                    "[class*='title']"

                ],

                query=query

            )

            if results:

                print(
                    f"Zepto -> {len(results)} products"
                )

                return results

        except Exception as e:

            print(
                "[Zepto] Error:",
                e
            )

    print(
        "Zepto -> 0 products"
    )

    return []


# =========================================================
# INSTAMART
# =========================================================

def scrape_instamart(page, query):

    print("\nOpening Instamart:")

    url = (
        "https://www.swiggy.com/"
        "instamart/search"
        "?custom_back=true&query="
        + quote(query)
    )

    print(url)

    try:

        try:
            page.set_extra_http_headers({
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "accept-language": "en-US,en;q=0.9",
                "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"'
            })
        except Exception:
            pass

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT
        )

        page.wait_for_timeout(
            WAIT_TIME
        )

        print(
            "[Instamart] URL:",
            page.url
        )

        if page_is_blocked(page):

            print(
                "[Instamart] REQUEST BLOCKED BY SWIGGY"
            )

            return []

        scroll_page(page)

        selectors = [

            "div[data-testid*='item']",

            "div[data-testid*='product']",

            "div[class*='ItemCard']",

            "div[class*='itemCard']",

            "div[class*='item-container']",

            "div[class*='product-card']",

            "div[class*='_2cT-i']",

            "a[href*='/instamart/item/']"

        ]

        results = generic_dom_extraction(

            page,

            selectors,

            [

                "div[data-testid='item-name']",

                "div[class*='itemName']",

                "div[class*='item-name']",

                "div[class*='name']",

                "div[class*='title']",

                "h1",
                "h2",
                "h3",
                "h4",
                "h5"

            ],

            query=query

        )

        print(
            f"Instamart -> {len(results)} products"
        )

        return results

    except Exception as e:

        print(
            "[Instamart] Error:",
            e
        )

        return []


# =========================================================
# BIGBASKET
# =========================================================

def scrape_bigbasket(page, query):

    print("\nOpening BigBasket:")

    url = (
        "https://www.bigbasket.com/ps/?q="
        + quote(query)
    )

    print(url)

    try:

        try:
            page.set_extra_http_headers({
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "accept-language": "en-US,en;q=0.9",
                "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"'
            })
        except Exception:
            pass

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT
        )

        page.wait_for_timeout(
            WAIT_TIME
        )

        print(
            "[BigBasket] URL:",
            page.url
        )

        if page_is_blocked(page):

            print(
                "[BigBasket] BLOCKED"
            )

            return []

        scroll_page(page)

        selectors = [

            "[data-qa='product']",

            "div[class*='ProductDeck']",

            "div[class*='SKUDeck']",

            "div[class*='ProductTemplate']",

            "li[class*='product']",

            "a[href*='/pd/']",

            "[data-testid*='product']",

            "[class*='ProductCard']",

            "[class*='product-card']"

        ]

        results = generic_dom_extraction(

            page,

            selectors,

            [

                "div[class*='name']",

                "div[class*='title']",

                "div[class*='product-name']",

                "h3",
                "h2",
                "h4"

            ],

            query=query

        )

        print(
            f"BigBasket -> {len(results)} products"
        )

        return results

    except Exception as e:

        print(
            "[BigBasket] Error:",
            e
        )

        return []


# =========================================================
# FIND BEST MATCH
# =========================================================

def find_best_match(
    base_product,
    candidates,
    used_indices
):

    best_index = None
    best_score = 0

    for index, candidate in enumerate(
        candidates
    ):

        if index in used_indices:
            continue

        score = product_match_score(
            base_product["name"],
            candidate["name"]
        )

        if score > best_score:

            best_score = score
            best_index = index

    if best_score >= 0.45:

        return best_index

    return None


# =========================================================
# ESTIMATION ENGINE
# =========================================================

def estimate_missing_prices(product):

    """
    Estimate unavailable platform prices using
    the average of at least two LIVE prices.

    Estimated prices are clearly marked and are
    NOT used to determine the winner.
    """

    live_prices = []

    for platform in PLATFORMS:

        key = platform.lower()

        price = product.get(key)

        source = product.get(
            f"{key}_source"
        )

        if (
            source == "live"
            and isinstance(
                price,
                (int, float)
            )
        ):

            live_prices.append(price)

    # -----------------------------------------------------
    # Need at least TWO real prices
    # -----------------------------------------------------

    if len(live_prices) < 2:

        return product

    average_price = round(
        sum(live_prices)
        / len(live_prices),
        2
    )

    # -----------------------------------------------------
    # Fill missing platforms
    # -----------------------------------------------------

    for platform in PLATFORMS:

        key = platform.lower()

        if product.get(key) is None:

            product[key] = average_price

            product[
                f"{key}_source"
            ] = "estimated"

    return product


# =========================================================
# COMBINE PRODUCTS
# =========================================================

def combine_products(platform_results):

    # -----------------------------------------------------
    # Choose platform with most actual products
    # -----------------------------------------------------

    base_platform = max(
        PLATFORMS,
        key=lambda platform:
        len(
            platform_results.get(
                platform,
                []
            )
        )
    )

    base_products = platform_results.get(
        base_platform,
        []
    )

    if not base_products:

        return []

    used = {
        platform: set()
        for platform in PLATFORMS
    }

    final_products = []

    # =====================================================
    # PROCESS BASE PRODUCTS
    # =====================================================

    for base_index, base in enumerate(
        base_products
    ):

        product = {

            "name":
                base["name"],

            "blinkit":
                None,

            "zepto":
                None,

            "instamart":
                None,

            "bigbasket":
                None,

            "blinkit_source":
                "unavailable",

            "zepto_source":
                "unavailable",

            "instamart_source":
                "unavailable",

            "bigbasket_source":
                "unavailable",

            "cheapest":
                "Unavailable"

        }

        # -------------------------------------------------
        # Base platform is LIVE
        # -------------------------------------------------

        base_key = base_platform.lower()

        product[base_key] = base["price"]

        product[
            f"{base_key}_source"
        ] = "live"

        used[
            base_platform
        ].add(base_index)

        # =================================================
        # MATCH OTHER PLATFORMS
        # =================================================

        for platform in PLATFORMS:

            if platform == base_platform:
                continue

            candidates = platform_results.get(
                platform,
                []
            )

            match_index = find_best_match(
                base,
                candidates,
                used[platform]
            )

            if match_index is not None:

                product[
                    platform.lower()
                ] = candidates[
                    match_index
                ]["price"]

                product[
                    f"{platform.lower()}_source"
                ] = "live"

                used[
                    platform
                ].add(match_index)

        # =================================================
        # ESTIMATE MISSING PRICES
        # =================================================

        product = estimate_missing_prices(
            product
        )

        # =================================================
        # DETERMINE WINNER USING ONLY LIVE PRICES
        # =================================================

        live_prices = {}

        for platform in PLATFORMS:

            key = platform.lower()

            price = product.get(key)

            source = product.get(
                f"{key}_source"
            )

            if (
                source == "live"
                and isinstance(
                    price,
                    (int, float)
                )
            ):

                live_prices[
                    platform
                ] = price

        if live_prices:

            lowest_price = min(
                live_prices.values()
            )

            winners = [
                platform
                for platform, price
                in live_prices.items()
                if price == lowest_price
            ]

            if len(winners) == 1:

                product["cheapest"] = (
                    winners[0]
                )

            else:

                product["cheapest"] = (
                    "Tie: "
                    + " / ".join(winners)
                )

        # -------------------------------------------------
        # Estimation status
        # -------------------------------------------------

        if any(
            product.get(
                f"{platform.lower()}_source"
            ) == "estimated"
            for platform in PLATFORMS
        ):

            product["has_estimates"] = True

        else:

            product["has_estimates"] = False

        final_products.append(
            product
        )

    # =====================================================
    # PROCESS REMAINING PRODUCTS FROM OTHER PLATFORMS
    # =====================================================

    for platform in PLATFORMS:

        if len(final_products) >= MAX_PRODUCTS:
            break

        candidates = platform_results.get(
            platform,
            []
        )

        for cand_index, cand in enumerate(candidates):

            if len(final_products) >= MAX_PRODUCTS:
                break

            if cand_index in used[platform]:
                continue

            product = {
                "name": cand["name"],
                "blinkit": None,
                "zepto": None,
                "instamart": None,
                "bigbasket": None,
                "blinkit_source": "unavailable",
                "zepto_source": "unavailable",
                "instamart_source": "unavailable",
                "bigbasket_source": "unavailable",
                "cheapest": "Unavailable"
            }

            cand_key = platform.lower()
            product[cand_key] = cand["price"]
            product[f"{cand_key}_source"] = "live"
            used[platform].add(cand_index)

            for other_platform in PLATFORMS:
                if other_platform == platform:
                    continue
                other_candidates = platform_results.get(other_platform, [])
                match_index = find_best_match(
                    cand,
                    other_candidates,
                    used[other_platform]
                )
                if match_index is not None:
                    product[other_platform.lower()] = other_candidates[match_index]["price"]
                    product[f"{other_platform.lower()}_source"] = "live"
                    used[other_platform].add(match_index)

            product = estimate_missing_prices(product)

            live_prices = {}
            for p_name in PLATFORMS:
                k = p_name.lower()
                price = product.get(k)
                source = product.get(f"{k}_source")
                if source == "live" and isinstance(price, (int, float)):
                    live_prices[p_name] = price

            if live_prices:
                lowest_price = min(live_prices.values())
                winners = [p_name for p_name, price in live_prices.items() if price == lowest_price]
                if len(winners) == 1:
                    product["cheapest"] = winners[0]
                else:
                    product["cheapest"] = "Tie: " + " / ".join(winners)

            product["has_estimates"] = any(
                product.get(f"{p_name.lower()}_source") == "estimated"
                for p_name in PLATFORMS
            )

            final_products.append(product)

    return final_products[:MAX_PRODUCTS]


# =========================================================
# MAIN SCRAPER
# =========================================================

def scrape_prices(query, location="mumbai"):

    loc_key = location.lower() if location else "mumbai"
    loc_info = LOCATIONS.get(loc_key, LOCATIONS["mumbai"])

    print("\n")
    print("=" * 50)
    print("       PRICESENSE LIVE SEARCH")
    print(f"       Query: {query}")
    print(f"       Location: {loc_info['name']} ({loc_info['pincode']})")
    print("=" * 50)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = browser.new_context(

            user_agent=USER_AGENT,

            viewport={
                "width": 1440,
                "height": 900
            },

            locale="en-IN",

            timezone_id="Asia/Kolkata",

            geolocation={
                "latitude": loc_info["lat"],
                "longitude": loc_info["lng"]
            },

            permissions=["geolocation"]

        )

        context.add_init_script(f"""
            Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
            const mockLat = {loc_info['lat']};
            const mockLng = {loc_info['lng']};
            if (navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition = function(success, error, options) {{
                    success({{
                        coords: {{
                            latitude: mockLat,
                            longitude: mockLng,
                            accuracy: 10
                        }},
                        timestamp: Date.now()
                    }});
                }};
            }}
        """)

        def run_scraper(scraper_func):
            page = context.new_page()
            try:
                return scraper_func(page, query)
            except Exception as e:
                print(f"Scraper error in {scraper_func.__name__}: {e}")
                return []
            finally:
                try:
                    page.close()
                except Exception:
                    pass

        try:

            platform_results = {

                "Blinkit":
                    run_scraper(scrape_blinkit),

                "Zepto":
                    run_scraper(scrape_zepto),

                "Instamart":
                    run_scraper(scrape_instamart),

                "BigBasket":
                    run_scraper(scrape_bigbasket)

            }

        finally:

            browser.close()

    # =====================================================
    # EXTRACTION REPORT
    # =====================================================

    print("\n")
    print("=" * 45)
    print("       RAW EXTRACTION SUMMARY")
    print("=" * 45)

    for platform in PLATFORMS:

        results = platform_results[
            platform
        ]

        print(
            f"{platform}: "
            f"{len(results)} products"
        )

        for product in results:

            print(
                f"  {product['name']}"
                f" -> ₹{product['price']}"
            )

    print("=" * 45)

    # =====================================================
    # COMBINE + ESTIMATE
    # =====================================================

    final_results = combine_products(
        platform_results
    )

    # =====================================================
    # FINAL REPORT
    # =====================================================

    print("\n")
    print("=" * 45)
    print("       FINAL PRICESENSE RESULTS")
    print("=" * 45)

    for product in final_results:

        print(
            f"\n{product['name']}"
        )

        for platform in PLATFORMS:

            key = platform.lower()

            print(
                f"  {platform}: "
                f"{product.get(key)} "
                f"[{product.get(key + '_source')}]"
            )

        print(
            f"  Verdict: "
            f"{product['cheapest']}"
        )

    print("=" * 45)

    return final_results


# =========================================================
# DIRECT TEST
# =========================================================

if __name__ == "__main__":

    results = scrape_prices(
        "Cadbury Dairy Milk"
    )

    for result in results:

        print(result)