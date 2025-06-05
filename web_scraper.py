@app.route('/scrape_oracle', methods=['GET'])
def scrape_oracle():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://docs.oracle.com/en/cloud/saas/readiness/erp/25b/ah25b/25B-accounting-hub-wn-t65682.html", timeout=60000)
        
        # 🕒 Wait for some key selector to ensure JS content loads
        page.wait_for_selector("div.wn-feature")  # This is Oracle's readiness feature block

        content = page.text_content("div.wn-feature")
        browser.close()
    return jsonify({'content': content})
