from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

@app.route("/scrape_oracle", methods=["GET"])
def scrape_oracle():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(5000)  # Wait for full load

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["nav", "footer", "header", "script", "style", "aside", "noscript"]):
            tag.decompose()

        content_tags = soup.select("main, article, section")

        if not content_tags:
            content_tags = soup.find_all("div")

        full_text = "\n".join(tag.get_text(separator=" ", strip=True) for tag in content_tags)

        # Strip out junk 404 or fallback content
        fallback_patterns = [
            r"We can't find the page",
            r"This page may have been moved",
            r"Oracle.com Home Page",
            r"Try search above",
            r"Subscribe to emails",
            r"Site Map",
            r"Country/Region"
        ]
        for pattern in fallback_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                return jsonify({"summary": "The page appears to be a 404 or generic Oracle site page. Please verify the URL."})

        summary = full_text.strip()
        if len(summary) > 30000:
            summary = summary[:30000] + "\n\n[Truncated due to length]"

        return jsonify({"summary": summary})

    except Exception as e:
        return jsonify({"summary": f"ERROR: {str(e)}"}), 500


@app.route("/", methods=["GET"])
def index():
    return "Oracle Web Scraper is Live. Use /scrape_oracle?url=YOUR_URL to extract content.", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
