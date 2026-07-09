from playwright.sync_api import sync_playwright

def extract_blinkit(query):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(f"https://blinkit.com/s/?q={query}", wait_until="domcontentloaded", timeout=30000)
        
        try:
            page.wait_for_selector("div[class*='Product__']", timeout=5000)
        except:
            pass
        
        items = page.locator("div[class*='Product__UpdatedDetailsContainer'], div.Product__Content-sc-11dk8zx-6").all()
        results = []
        for el in items[:3]:
            text = el.inner_text().replace('\n', ' ')
            results.append(text)
            print("Found:", text)
            
        # Also try simpler a tag or data-testid if above fails
        if not results:
            print("Trying fallback selectors")
            els = page.locator("a > div").all()
            for el in els[:10]:
                text = el.inner_text().replace('\n', ' ')
                if '₹' in text:
                    results.append(text)
                    print("Found Fallback:", text)

        browser.close()

if __name__ == "__main__":
    extract_blinkit("milk")
