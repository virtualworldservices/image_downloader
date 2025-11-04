import os
import time
import requests
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

def clean_filename(name):
    import re
    return re.sub(r'[\\/*?:"<>|]', "_", name)

# --- Input base URL ---
base_url = input("Enter the base URL (e.g., https://example.com/): ").strip()
if not base_url.startswith("http"):
    base_url = "https://" + base_url

# --- Setup Selenium ---
options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--start-maximized")
options.add_argument("--headless")  # <-- Add this line to enable headless mode
options.add_argument("--disable-gpu")  # Recommended for headless Chrome
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)
actions = ActionChains(driver)

# --- Prepare folder ---
domain_name = urlparse(base_url).netloc.replace("www.", "")
folder_path = os.path.join(os.getcwd(), domain_name)
os.makedirs(folder_path, exist_ok=True)

# --- Crawl ---
visited_pages = set()
to_visit = {base_url}
downloaded_images = set()

while to_visit:
    url = to_visit.pop()
    if url in visited_pages:
        continue
    if any(skip in url.lower() for skip in ["contact", "about", "quality", "admin", "admin2", "pdf", "service", "services", "jpg", "press", "news", "webp", "pinterest", "facebook", "instagram", "twitter", "youtube"]):
        continue

    visited_pages.add(url)
    driver.get(url)
    print(f"\nVisiting page: {url}")
    time.sleep(2)

    # --- Collect internal links ---
    try:
        links_on_page = driver.find_elements(By.XPATH, "//a[@href]")
        for link in links_on_page:
            href = link.get_attribute("href")
            if href:
                if urlparse(href).netloc == urlparse(base_url).netloc:
                    if href not in visited_pages and not any(skip in href.lower() for skip in ["contact", "about"]):
                        to_visit.add(href)
    except:
        pass

    # --- Page-based name from URL ---
    path_parts = [p for p in urlparse(url).path.split("/") if p]
    page_name = "_".join([clean_filename(part.capitalize()) for part in path_parts[-2:]]) \
                if len(path_parts) >= 2 else (clean_filename(path_parts[-1].capitalize()) if path_parts else "home")

    # --- Find .jpg and .webp links ---
    image_links = driver.find_elements(By.XPATH,
        "//a[substring(@href, string-length(@href)-3)='.jpg' or substring(@href, string-length(@href)-4)='.webp']"
    )

    for idx, link in enumerate(image_links, start=1):
        try:
            href = link.get_attribute("href")
            if not href or href in downloaded_images:
                continue

            # Scroll and click
            driver.execute_script("arguments[0].scrollIntoView(true);", link)
            actions.move_to_element(link).perform()
            time.sleep(0.5)
            try:
                link.click()
                time.sleep(1)
            except:
                pass

            # Download image
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
print(f"\nAll images saved to: {folder_path}")
