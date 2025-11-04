from flask import Flask, render_template, request, jsonify
import os
import time
import requests
import re
import threading
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

app = Flask(__name__)

# --- Helper ---
def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def get_chrome_options():
    """Configure Chrome for Heroku (headless)."""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    return chrome_options

def crawl_images(base_url):
    if not base_url.startswith("http"):
        base_url = "https://" + base_url

    options = get_chrome_options()
    driver = webdriver.Chrome(
        executable_path=os.environ.get("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver"),
        options=options
    )
    actions = ActionChains(driver)

    domain_name = urlparse(base_url).netloc.replace("www.", "")
    folder_path = os.path.join(os.getcwd(), "downloads", domain_name)
    os.makedirs(folder_path, exist_ok=True)

    visited_pages = set()
    to_visit = {base_url}
    downloaded_images = set()

    while to_visit:
        url = to_visit.pop()
        if url in visited_pages:
            continue
        if any(skip in url.lower() for skip in [
            "contact", "about", "quality", "admin", "pdf", "service", "press",
            "news", "facebook", "instagram", "twitter", "youtube", "pinterest"
        ]):
            continue

        visited_pages.add(url)
        print(f"Visiting page: {url}")
        try:
            driver.get(url)
        except:
            continue
        time.sleep(2)

        # --- Collect links ---
        try:
            links_on_page = driver.find_elements(By.XPATH, "//a[@href]")
            for link in links_on_page:
                href = link.get_attribute("href")
                if href and urlparse(href).netloc == urlparse(base_url).netloc:
                    if href not in visited_pages:
                        to_visit.add(href)
        except:
            pass

        # --- Page name ---
        path_parts = [p for p in urlparse(url).path.split("/") if p]
        page_name = (
            "_".join([clean_filename(p.capitalize()) for p in path_parts[-2:]])
            if len(path_parts) >= 2 else
            (clean_filename(path_parts[-1].capitalize()) if path_parts else "home")
        )

        # --- Find .jpg/.webp links ---
        image_links = driver.find_elements(
            By.XPATH,
            "//a[substring(@href, string-length(@href)-3)='.jpg' or substring(@href, string-length(@href)-4)='.webp']"
        )

        for idx, link in enumerate(image_links, start=1):
            try:
                href = link.get_attribute("href")
                if not href or href in downloaded_images:
                    continue
                driver.execute_script("arguments[0].scrollIntoView(true);", link)
                actions.move_to_element(link).perform()
                print(f"Downloading: {href}")
                response = requests.get(href)
                if response.status_code == 200:
                    ext = href.split('.')[-1].split('?')[0]
                    file_name = os.path.join(folder_path, f"{page_name}_{idx}.{ext}")
                    with open(file_name, "wb") as f:
                        f.write(response.content)
                    downloaded_images.add(href)
            except Exception as e:
                print(f"Skipping image due to error: {e}")
                continue

    driver.quit()
    print(f"All images saved to: {folder_path}")
    return folder_path

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/crawl", methods=["POST"])
def start_crawl():
    base_url = request.form.get("url")
    if not base_url:
        return jsonify({"error": "URL is required"}), 400

    thread = threading.Thread(target=crawl_images, args=(base_url,))
    thread.start()

    return jsonify({"message": f"Crawling started for {base_url}."})

if __name__ == "__main__":
    os.makedirs("downloads", exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
