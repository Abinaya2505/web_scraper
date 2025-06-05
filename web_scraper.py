from flask import Flask, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route('/scrape_oracle', methods=['GET'])
def scrape_oracle():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://docs.oracle.com/en/cloud/saas/readiness/erp/25b/ah25b/25B-accounting-hub-wn-t65682.html", timeout=90000)

        # ✅ Wait for key content to load
        page.wait_for_selector("div.section")

        # Extract readable feature content
        content = page.inner_text("body")

        browser.close()
    return jsonify({'content': content})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
