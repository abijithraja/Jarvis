import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def _make_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def search_google(query: str) -> str:
    """Search Google and return top result titles."""
    driver = None
    try:
        driver = _make_driver(headless=True)
        driver.get("https://www.google.com")

        box = driver.find_element(By.NAME, "q")
        box.send_keys(query)
        box.send_keys(Keys.RETURN)

        time.sleep(2)

        results = driver.find_elements(By.CSS_SELECTOR, "h3")
        titles = [r.text for r in results[:3] if r.text]

        if titles:
            return "Top results: " + " | ".join(titles)
        return f"Search done for: {query}"

    except Exception as e:
        return f"Browser search failed: {str(e)}"
    finally:
        if driver:
            driver.quit()


def open_url_and_read(url: str) -> str:
    """Open a URL and return the visible page text (first 500 chars)."""
    driver = None
    try:
        driver = _make_driver(headless=True)
        driver.get(url)
        time.sleep(2)
        body = driver.find_element(By.TAG_NAME, "body")
        return body.text[:500]
    except Exception as e:
        return f"Could not read page: {str(e)}"
    finally:
        if driver:
            driver.quit()
