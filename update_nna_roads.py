from playwright.sync_api import sync_playwright

url = "https://nna-leb.gov.lb/en/search?q=road+status"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(5000)

    anchors = page.locator("a")
    count = anchors.count()
    print("Total anchors found:", count)

    for i in range(min(count, 40)):
        a = anchors.nth(i)
        text = a.inner_text().strip()
        href = a.get_attribute("href")
        print(f"{i+1}. TEXT: {text}")
        print(f"   HREF: {href}")
        print("-" * 60)

    browser.close()