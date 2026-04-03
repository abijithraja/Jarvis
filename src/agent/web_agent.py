import requests
from bs4 import BeautifulSoup


def search_and_summarize(query: str) -> str:
    """
    Search DuckDuckGo (no API key needed) and return a short summary
    of the top result.
    """
    query = query.strip()
    if not query:
        return "What would you like me to search for?"

    try:
        # DuckDuckGo instant answer API
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        headers = {"User-Agent": "Jarvis/1.0"}

        r = requests.get(url, params=params, headers=headers, timeout=6)
        data = r.json()

        # Try AbstractText first (Wikipedia snippet)
        abstract = data.get("AbstractText", "").strip()
        if abstract:
            return abstract[:300]

        # Try Answer (e.g. math, conversions)
        answer = data.get("Answer", "").strip()
        if answer:
            return answer

        # Try related topics
        topics = data.get("RelatedTopics", [])
        for topic in topics[:2]:
            if isinstance(topic, dict) and topic.get("Text"):
                return topic["Text"][:300]

        # Fallback: open the result in browser
        from src.agent.external_agent import _open_url
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        _open_url(search_url)
        return f"Opened Google search for: {query}"

    except Exception as e:
        return f"Search failed: {str(e)}"
