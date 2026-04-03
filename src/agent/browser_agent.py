from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time


def search_google(query):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get("https://www.google.com")

    box = driver.find_element(By.NAME, "q")
    box.send_keys(query)
    box.send_keys(Keys.RETURN)

    time.sleep(2)

    results = driver.find_elements(By.CSS_SELECTOR, "h3")

    if results:
        results[0].click()

    return f"Searching Google for {query}"
