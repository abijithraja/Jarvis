import requests
from bs4 import BeautifulSoup


def search_and_summarize(query):
    url = f"https://www.google.com/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")

    results = soup.select("div.BNeawe")

    if results:
        return results[0].text

    return "No result found"
