from flask import Flask, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route('/scrape_oracle', methods=['GET'])
def scrape_oracle():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://docs.oracle.com/en/cloud/saas/readiness/erp/25b/ah25b/25B-accounting-hub-wn-t65682.html", timeout=60000)
        content = page.text_content("body")
        browser.close()
    return jsonify({'content': content})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
