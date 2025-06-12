from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

app = Flask(__name__)

def fetch_page_with_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        html = page.content()
        browser.close()
        return html

def is_valid_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text().lower()
    junk_keywords = [
        "we can't find the page", 
        "the page may have been moved",
        "not found", 
        "404 error", 
        "try search above"
    ]
    for keyword in junk_keywords:
        if keyword in page_text:
            return False
    return True

def extract_main_content(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Try primary content sections used in Oracle readiness pages
    for selector in ['div#main-content', 'div.main-content', 'div.content', 'body']:
        main = soup.select_one(selector)
        if main:
            return main.get_text(separator="\n", strip=True)

    return "No readable content found on the page."

def generate_summary(text):
    if len(text.strip()) < 500:
        return "Document too short or lacks meaningful update content."

    # Placeholder: Replace this with OpenAI or your structured summarizer
    return f"📄 Scraped Content Preview:\n\n{text[:1500]}...\n\n[Truncated for brevity]"

@app.route("/scrape_oracle")
def scrape_oracle():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL parameter is required."}), 400

    try:
        html = fetch_page_with_playwright(url)
        if not is_valid_content(html):
            return jsonify({"error": "Invalid or 404 page content detected."}), 400

        main_text = extract_main_content(html)
        summary = generate_summary(main_text)
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
