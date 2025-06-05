from flask import Flask, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

@app.route('/scrape_oracle', methods=['GET'])
def scrape_oracle():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            page.goto("https://docs.oracle.com/en/cloud/saas/readiness/erp/25b/ah25b/25B-accounting-hub-wn-t65682.html", timeout=60000)

            # ✅ Wait until DOM is fully loaded
            page.wait_for_load_state('networkidle', timeout=30000)

            # ✅ Now extract the full body or specific section
            content = page.text_content("body")  # or use a better selector if needed
            browser.close()

            return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
