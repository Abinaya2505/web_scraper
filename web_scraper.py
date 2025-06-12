from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# Fallback phrases to detect invalid or generic pages
fallback_patterns = [
    "We can't find the page",
    "Page Not Found",
    "Error 404",
    "Try search above",
    "Oracle.com Home Page",
    "Sitemap",
    "Privacy/Do Not Sell My Info"
]

def is_valid_content(text):
    for pattern in fallback_patterns:
        if pattern.lower() in text.lower():
            return False
    return True

@app.route('/scrape_oracle')
def scrape_oracle():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)  # 60 sec timeout
            page.wait_for_timeout(3000)  # wait 3s for content
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'html.parser')

        # Try to extract only useful main content
        main_content = soup.find('div', class_='page-content') or soup.find('main') or soup.body

        # Clean the text
        text = main_content.get_text(separator="\n", strip=True)

        # Check if the content is valid (not a fallback page)
        if not is_valid_content(text) or len(text) < 500:
            return jsonify({
                'summary': "The AI rejected the content. Please verify that the source has meaningful Oracle-related content."
            })

        # Return raw extracted text
        return jsonify({
            'summary': text[:10000]  # limit response size
        })

    except Exception as e:
        return jsonify({'error': f'Exception occurred: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
