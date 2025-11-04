from flask import Flask, render_template, request, send_file, redirect, url_for
import os
import requests
import re
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
import tempfile

app = Flask(__name__)

# --- Helper ---
def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def get_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = "/app/.chrome-for-testing/chrome-linux64/chrome"
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    return chrome_options

def crawl_images(base_url, max_images=30):
    if not base_url.startswith("http"):
        base_url = "https://" + base_url

    chrome_options = get_chrome_options()
    service = Service("/app/.chrome-for-testing/chromedriver-linux64/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    actions = ActionChains(driver)

    images_data = []
    visited_pages = set()
    to_visit = {base_url}

    while to_visit and len(images_data) < max_images:
        url = to_visit.pop()
        if url in visited_pages:
            continue
        visited_pages.add(url)

        try:
            driver.get(url)
        except:
            continue

        # collect internal links
        try:
            links_on_page = driver.find_elements(By.XPATH, "//a[@href]")
            for link in links_on_page:
                href = link.get_attribute("href")
                if href and urlparse(href).netloc == urlparse(base_url).netloc:
                    if href not in visited_pages:
                        to_visit.add(href)
        except:
            pass

        # page name
        path_parts = [p for p in urlparse(url).path.split("/") if p]
        page_name = (
            "_".join([clean_filename(p.capitalize()) for p in path_parts[-2:]])
            if len(path_parts) >= 2 else
            (clean_filename(path_parts[-1].capitalize()) if path_parts else "home")
        )

        # find .jpg/.webp links
        image_links = driver.find_elements(
            By.XPATH,
            "//a[substring(@href, string-length(@href)-3)='.jpg' or substring(@href, string-length(@href)-4)='.webp']"
        )

        for idx, link in enumerate(image_links, start=1):
            if len(images_data) >= max_images:
                break
            href = link.get_attribute("href")
            if not href:
                continue

            ext = href.split('.')[-1].split('?')[0]
            images_data.append({
                "url": href,
                "display_name": f"{page_name}_{idx}.{ext}"
            })

    driver.quit()
    return images_data

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    page = int(request.args.get("page", 1))
    images = []
    url = ""

    if request.method == "POST":
        url = request.form.get("url")
        if url:
            # Save images to session temp folder
            images = crawl_images(url)
            request.environ['images_data'] = images  # Store in request temporarily
            return render_template("index.html", images=images[0:10], page=1, total=len(images), url=url)

    # GET request: handle next/prev page
    images = request.environ.get('images_data', [])
    start = (page-1)*10
    end = start + 10
    return render_template("index.html", images=images[start:end], page=page, total=len(images), url=url)

@app.route("/download/<path:filepath>")
def download_file(filepath):
    return send_from_directory("static/downloads", filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))





