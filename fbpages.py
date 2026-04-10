from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PAGE_NAME  = "SattaMatkaai"           # Exact name of your Facebook Page
KEYWORDS   = ["satta matka", "kalyan "]
MAX_JOINS  = 15                          # Max groups to join per keyword
DELAY_MIN  = 45                         # Min seconds between joins
DELAY_MAX  = 120                        # Max seconds between joins
CHROMEDRIVER_PATH = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\chromedriver145.exe"
# ──────────────────────────────────────────────────────────────────────────────


def create_driver():
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    logging.info("Connected to existing Chrome session!")
    return driver


def is_logged_in(driver):
    driver.get("https://www.facebook.com/")
    time.sleep(random.uniform(3, 5))
    if "login" in driver.current_url:
        logging.warning("Not logged in! Please log in manually in Chrome first.")
        input("Press ENTER after logging into Facebook manually...")
    else:
        logging.info("Already logged into Facebook!")


def switch_to_page(driver, page_name):
    driver.get("https://www.facebook.com/")
    time.sleep(random.uniform(3, 5))
    try:
        menu_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH,
                "//div[@aria-label='Account' or @aria-label='Your profile']"
            ))
        )
        menu_btn.click()
        time.sleep(random.uniform(2, 3))

        page_option = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH,
                f"//*[contains(text(), '{page_name}')]"
            ))
        )
        page_option.click()
        time.sleep(random.uniform(3, 5))
        logging.info(f"Switched to Page: {page_name}")

    except Exception as e:
        logging.warning(f"Auto-switch failed: {e}")
        logging.info("Please switch to your Page manually in the browser now...")
        input("Press ENTER after switching to your Page manually...")


def search_and_join_groups(driver, keyword, max_joins):
    joined = 0
    search_url = f"https://www.facebook.com/search/groups/?q={keyword.replace(' ', '%20')}"
    driver.get(search_url)
    time.sleep(random.uniform(4, 7))

    # Scroll to load more results
    for _ in range(4):
        driver.execute_script(f"window.scrollBy(0, {random.randint(300, 700)});")
        time.sleep(random.uniform(1, 2))

    results = driver.find_elements(
        By.XPATH, "//div[@role='article']//a[contains(@href, '/groups/')]"
    )

    group_urls = list(set([
        r.get_attribute("href") for r in results
        if r.get_attribute("href") and "/groups/" in r.get_attribute("href")
    ]))

    logging.info(f"Found {len(group_urls)} groups for: '{keyword}'")

    if len(group_urls) == 0:
        logging.warning("No groups found. Facebook may have changed its layout.")
        return 0

    for url in group_urls:
        if joined >= max_joins:
            break
        try:
            driver.get(url)
            time.sleep(random.uniform(3, 6))

            # Scroll a bit to trigger page load
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(random.uniform(1, 2))

            join_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//*[contains(text(),'Join group') or "
                    "contains(text(),'Join Group') or "
                    "contains(text(),'Join')]"
                ))
            )
            join_btn.click()
            joined += 1
            logging.info(f"Joined ({joined}/{max_joins}): {url}")

            wait = random.randint(DELAY_MIN, DELAY_MAX)
            logging.info(f"Waiting {wait}s before next join...")
            time.sleep(wait)

        except Exception as e:
            logging.warning(f"Skipped: {url} - {e}")
            time.sleep(random.uniform(5, 10))

    return joined


def main():
    driver = create_driver()

    is_logged_in(driver)
    switch_to_page(driver, PAGE_NAME)

    total = 0
    for keyword in KEYWORDS:
        logging.info(f"--- Searching keyword: '{keyword}' ---")
        count = search_and_join_groups(driver, keyword, MAX_JOINS)
        total += count
        logging.info(f"Joined {count} groups for '{keyword}'")

        if keyword != KEYWORDS[-1]:  # No pause after last keyword
            pause = random.randint(60, 180)
            logging.info(f"Pausing {pause}s before next keyword...")
            time.sleep(pause)

    logging.info(f"Done! Total groups joined: {total}")


if __name__ == "__main__":
    main()