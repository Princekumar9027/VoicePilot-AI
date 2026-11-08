
from html.parser import HTMLParser

import httpx


class DuckDuckGoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_kind = None
        self.current_text = []
        self.current_depth = 0
        self.current_result = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()

        if tag == "a" and "result__a" in classes:
            self.current_result = {
                "title": "",
                "url": attrs.get("href", ""),
                "snippet": "",
            }
            self.current_kind = "title"
            self.current_text = []
            self.current_depth = 1

        elif self.current_result and (
            "result__snippet" in classes
        ):
            self.current_kind = "snippet"
            self.current_text = []
            self.current_depth = 1

        elif self.current_kind:
            self.current_depth += 1

    def handle_data(self, data):
        if self.current_kind:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if not self.current_kind:
            return

        self.current_depth -= 1

        if self.current_depth <= 0:
            text = " ".join(" ".join(self.current_text).split())

            if self.current_kind == "title" and self.current_result:
                self.current_result["title"] = text
                self.results.append(self.current_result)

            elif self.current_kind == "snippet" and self.results:
                self.results[-1]["snippet"] = text

            self.current_kind = None
            self.current_text = []
            self.current_depth = 0
            self.current_result = None


def search_web(query: str, max_results: int = 5) -> dict:
    query = query.strip()

    if not query:
        return {"query": query, "results": [], "count": 0}

    if len(query) > 500:
        raise ValueError("Search query is too long")

    url = "https://html.duckduckgo.com/html/"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        )
    }

    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        response = client.get(
            url,
            params={"q": query},
            headers=headers,
        )
        response.raise_for_status()

    parser = DuckDuckGoParser()
    parser.feed(response.text)

    results = [
        result
        for result in parser.results
        if result["title"] and result["url"]
    ][:max_results]

    return {
        "query": query,
        "results": results,
        "count": len(results),
    }
