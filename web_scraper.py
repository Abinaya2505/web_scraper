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
            page.wait_for_timeout(5000)  # Wait for page to fully load

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted tags
        for tag in soup(["nav", "footer", "header", "script", "style", "aside", "noscript"]):
            tag.decompose()

        # Try structured sections first
        content_tags = soup.select("main, article, section")

        # Fallback: if those aren't found, use divs with meaningful text
        if not content_tags:
            content_tags = soup.find_all("div")

        # Extract clean text
        full_text = "\n".join(tag.get_text(separator=" ", strip=True) for tag in content_tags)

        # Sanitize: remove 404 fallback, menus, and social junk
        fallback_patterns = [
            r"We can't find the page",
            r"This page may have been moved",
            r"Oracle.com Home Page",
            r"Try search above",
            r"Subscribe to emails",
            r"Site Map",
            r"Country/Region",
        ]

        for pattern in fallback_patterns:
