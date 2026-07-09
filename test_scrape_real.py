from playwright.sync_api import sync_playwright
import time

def scrape_blinkit(query):
    with sync_playwright() as p:
        # User wants real prices. We'll use headless=False to bypass basic bot protection.
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        print("Goto Blinkit")
        page.goto(f"https://blinkit.com/s/?q={query}", wait_until="domcontentloaded", timeout=30000)
        
        # Wait for either products to load or bot challenge
        try:
            # We wait for the product price element or a known product class
            page.wait_for_selector("div[class*='Product__']", timeout=5000)
        except:
            pass
        
        html = page.content()
        browser.close()
        return html

if __name__ == "__main__":
    html = scrape_blinkit("milk")
    with open("test_out.html", "w") as f:
        f.write(html)
    print("Scraped length:", len(html))
