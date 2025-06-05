"""
Oracle SaaS Readiness Scraper
- Crawls every module on the landing page
- Uses Playwright to render JavaScript-injected navigation
- Handles "Next Page" pagination
- Extracts all HTML/PDF content, tables, and images
- Outputs a single Markdown report
"""

import requests
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin
import re
from io import BytesIO
from pdfminer.high_level import extract_text
from playwright.sync_api import sync_playwright
from flask import Flask
import certifi
import os

app = Flask(__name__)

LOG_FILE = "oracle_readiness_report_paginated.md"

def log(message="", end="\n"):
    print(message, end=end)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + ("" if end == "" else end))

def get_landing_tiles():
    base_url = "https://docs.oracle.com/en/cloud/saas/readiness/index.html"
    resp = requests.get(base_url, verify=False)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return [(a.get_text(strip=True), urljoin(base_url, a["href"]))
            for a in soup.select("h3 > a")]

def fetch_rendered_dom_all_pages(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            page.goto(url, wait_until="load", timeout=60000)
            page.wait_for_timeout(2000)
        except Exception as e:
            log(f"[ERROR] Failed to load {url}: {e}")
            browser.close()
            return None

        full_content = ""
        seen_pages = set()

        while True:
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            main = soup.find("main")
            if not main:
                browser.close()
                return None

            content = str(main)
            if content in seen_pages:
                break

            log("\n" + "="*80)
            log(f"📄 Extracted Page Content ({url}):")
            log("="*80)
            log(main.get_text(separator="\n", strip=True))
            log("="*80 + "\n")

            full_content += content + "\n<!-- PAGE BREAK -->\n"
            seen_pages.add(content)

            try:
                next_btn = page.locator("text=Next Page")
                if next_btn.is_visible() and next_btn.is_enabled():
                    next_btn.click()
                    page.wait_for_timeout(2000)
                else:
                    break
            except Exception:
                break

        browser.close()
    return BeautifulSoup(full_content, "html.parser")

def fetch_html_navigation(soup, base_url):
    nav_tag = soup.find('nav')
    if not nav_tag:
        return None

    def recurse(ul, depth=0):
        lines = []
        for li in ul.find_all('li', recursive=False):
            a = li.find('a', href=True)
            text = a.get_text(strip=True) if a else li.get_text(strip=True)
            href = urljoin(base_url, a['href']) if a else None
            prefix = '  ' * depth + '- '
            lines.append(f"{prefix}[{text}]({href})" if href else prefix + text)
            sub_ul = li.find('ul')
            if sub_ul:
                lines.extend(recurse(sub_ul, depth+1))
        return lines

    top_ul = nav_tag.find('ul')
    return "\n".join(recurse(top_ul)) if top_ul else None

def fetch_html_content(html_url):
    soup = fetch_rendered_dom_all_pages(html_url)
    if not soup:
        return None

    nav_md = fetch_html_navigation(soup, html_url)
    main = soup.find('main') or soup
    parts = []

    for tag in main.find_all(['h1','h2','h3','h4','p','li','table','img','div','span']):
        if tag.name in ['h1','h2','h3','h4','p','li']:
            text = tag.get_text(strip=True)
            if text:
                parts.append(text)
        elif tag.name == 'table':
            rows = []
            for tr in tag.find_all('tr'):
                cells = [c.get_text(strip=True) for c in tr.find_all(['th','td'])]
                if cells:
                    rows.append('| ' + ' | '.join(cells) + ' |')
            if rows:
                parts.append('\n'.join(rows))
        elif tag.name == 'img':
            src = tag.get('src')
            if src:
                parts.append(f"[Image] {urljoin(html_url, src)}")

    content_md = "\n\n".join(parts)
    if nav_md:
        return f"__START OF NAV__\n\n{nav_md}\n\n__END OF NAV__\n\n{content_md}"
    return content_md

def fetch_pdf_content(pdf_url):
    r = requests.get(pdf_url, verify=False)
    r.raise_for_status()
    return extract_text(BytesIO(r.content))

def get_module_updates(module_url):
    soup = fetch_rendered_dom_all_pages(module_url)
    if not soup:
        return []

    updates = {}
    for a in soup.find_all('a', string=re.compile(r'^(HTML|PDF)$')):
        label = a.get_text(strip=True)
        href = urljoin(module_url, a['href'])
        is_pdf = href.lower().split('?')[0].endswith('.pdf')

        section_title = None
        for sib in a.previous_siblings:
            if getattr(sib, 'name', None) in ['h1','h2','h3','h4','h5','h6']:
                t = sib.get_text(strip=True)
                if t:
                    section_title = t
                    break
        if not section_title:
            prev = a.previous_element
            while prev and (not isinstance(prev, NavigableString) or not prev.strip()):
                prev = prev.previous_element
            section_title = prev.strip() if prev else '(no title)'

        content = fetch_pdf_content(href) if is_pdf else fetch_html_content(href)
        if content is None:
            continue

        updates.setdefault(section_title, []).append({
            'label': label,
            'url': href,
            'content': content,
        })

    return [{'section': sec, 'entries': entries} for sec, entries in updates.items()]

def write_report(modules):
    log(f"Writing report to {LOG_FILE} ...")
    for module in modules:
        section_output = f"# {module['name']}\n\n"
        log(section_output, end='')

        for sec in module['updates']:
            sec_title = f"## {sec['section']}\n\n"
            log(sec_title, end='')

            for e in sec['entries']:
                topic_line = f"**Topic: {sec['section']}**\n"
                url_line = f"**[{e['label']}] {e['url']}**\n\n"
                content_start = "__START OF CONTENT__\n\n"
                content_body = e['content'].strip() + "\n\n" if e['content'] else "(No content available)\n\n"
                content_end = "__END OF CONTENT__\n\n"
                divider = "---\n\n"

                entry_output = (
                    topic_line +
                    url_line +
                    content_start +
                    content_body +
                    content_end +
                    divider
                )

                log(entry_output, end='')

    log(f"\n✅ Report written to {LOG_FILE}")

def main():
    # Clear the previous .md log at start
    open(LOG_FILE, "w", encoding="utf-8").close()
    
    log(f"Current working directory: {os.getcwd()}")
    visited = set()
    all_tiles = get_landing_tiles()
    modules = []    

    for name, url in all_tiles:
        if url in visited:
            continue
        log(f"\n>>> Fetching updates for: {name}")
        updates = get_module_updates(url)

        if not any(u['entries'] for u in updates):
            log(f"[WARN] Skipping {name} - No <main> tag or empty content.")
            continue

        modules.append({'name': name, 'updates': updates})
        visited.add(url)

        # Refresh tiles in case dynamic structure changes
        all_tiles = get_landing_tiles()

    log(f"Total modules to write: {len(modules)}")
    write_report(modules)

if __name__ == "__main__":
    main()
