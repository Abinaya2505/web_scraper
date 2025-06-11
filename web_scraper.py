from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import subprocess
import os

app = Flask(__name__)

# Ensure Playwright browser binaries are installed
try:
    subprocess.run(["playwright", "install", "chromium"], check=True)
except Exception as e:
    print(f"Browser install failed: {str(e)}")

@app.route("/scrape_oracle", methods=["GET"])
def scrape_oracle():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing URL parameter"}), 400

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Go to the URL and wait for all network activity to finish
            page.goto(url, timeout=60000, wait_until="networkidle")

            # Scroll to bottom to load dynamic content
            page.evaluate(
                """() => {
                    return new Promise(resolve => {
                        let totalHeight = 0;
                        const distance = 500;
                        const timer = setInterval(() => {
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= document.body.scrollHeight) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 200);
                    });
                }"""
            )

            page.wait_for_selector("body", timeout=10000)
visible_text = page.inner_text("body")
            browser.close()

        # Clean HTML with BeautifulSoup
soup = BeautifulSoup(visible_text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        raw_text = soup.get_text(separator='\n')
        cleaned_text = '\n'.join(line.strip() for line in raw_text.splitlines() if line.strip())

        if len(cleaned_text) < 500:
            return jsonify({"error": "Extracted content is too short or not meaningful."}), 422

        return jsonify({"content": cleaned_text[:60000]})  # Increased from 30000

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# Required entry point for Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
