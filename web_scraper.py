from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route("/scrape_oracle", methods=["GET"])
def scrape_oracle():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing URL parameter"}), 400

    try:
        # Safely fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML and clean it
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        raw_text = soup.get_text(separator='\n')
        cleaned_text = '\n'.join(line.strip() for line in raw_text.splitlines() if line.strip())

        # Return only if there's actual readable content
        if len(cleaned_text) < 500:
            return jsonify({"error": "Extracted content is too short or not meaningful."}), 422

        return jsonify({"content": cleaned_text[:30000]})  # Trim if very large

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"HTTP request failed: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

