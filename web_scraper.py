from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re

app = Flask(__name__)

@app.route('/scrape_oracle', methods=['GET'])
def scrape_oracle():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')

        # ✅ Extract meaningful content from known Oracle structure
        main_content = soup.find('div', class_='main-content') or soup.find('main') or soup.body
        text = main_content.get_text(separator='\n', strip=True) if main_content else soup.get_text(separator='\n', strip=True)

        # ✅ Remove known junk patterns
        fallback_patterns = [
            r"We can't find the page",
            r"Subscribe to emails",
            r"Oracle.com Home Page",
            r"Try Oracle Cloud Free Tier",
            r"\b(View|Sign In|Careers|Sitemap|Ad Choices|Country/Region|Privacy)\b",
            r"\b202[0-5] Oracle\b",
        ]
        for pattern in fallback_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return jsonify({"content": "", "summary": "ERROR: Fallback or junk content detected"}), 200

        # ✅ Short-circuit if text is too generic or short
        if len(text.strip()) < 500:
            return jsonify({"content": "", "summary": "ERROR: Not enough meaningful content extracted"}), 200

        return jsonify({"content": text.strip()})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
