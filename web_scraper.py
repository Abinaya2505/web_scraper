from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/scrape_oracle")
def scrape():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Strip scripts, styles, and clean
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        visible_text = soup.get_text(separator='\n')
        clean_text = '\n'.join(line.strip() for line in visible_text.splitlines() if line.strip())

        return jsonify({"content": clean_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
