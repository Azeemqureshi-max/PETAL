import urllib.parse
import urllib.request
from html.parser import HTMLParser


class SearchResultParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.results = []

        self.current_url = None
        self.current_text = []

        self.in_result_link = False

    def handle_starttag(self, tag, attrs):

        attrs = dict(attrs)

        if tag != "a":
            return

        classes = attrs.get("class", "")

        if "result__a" not in classes:
            return

        self.current_url = attrs.get("href")

        self.current_text = []

        self.in_result_link = True

    def handle_data(self, data):

        if self.in_result_link:
            self.current_text.append(data)

    def handle_endtag(self, tag):

        if tag == "a" and self.in_result_link:

            title = "".join(
                self.current_text
            ).strip()

            if title and self.current_url:

                url = clean_url(
                    self.current_url
                )

                if is_valid_result_url(url):

                    self.results.append(
                        {
                            "title": title,
                            "url": url
                        }
                    )

            self.current_url = None

            self.current_text = []

            self.in_result_link = False


def clean_url(url):

    if not url:
        return ""

    # DuckDuckGo redirect URL
    if "uddg=" in url:

        parsed = urllib.parse.urlparse(url)

        parameters = urllib.parse.parse_qs(
            parsed.query
        )

        if "uddg" in parameters:

            url = parameters["uddg"][0]

    # Protocol-relative URL
    if url.startswith("//"):

        url = "https:" + url

    # Parse URL
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in (
        "http",
        "https"
    ):
        return ""

    if not parsed.netloc:
        return ""

    # Remove accidental search-result
    # query corruption.
    query = parsed.query

    if query:

        # Reject obviously broken queries such as:
        # Python?Python
        if "?" in query:
            query = ""

    # Rebuild clean URL
    return urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "/",
            "",
            query,
            ""
        )
    )


def is_valid_result_url(url):

    if not url:
        return False

    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in (
        "http",
        "https"
    ):
        return False

    hostname = (
        parsed.hostname or ""
    ).lower()

    blocked_hosts = {
        "duckduckgo.com",
        "www.duckduckgo.com",
        "bing.com",
        "www.bing.com"
    }

    if hostname in blocked_hosts:
        return False

    return True


def search_web(query, max_results=5):

    query = query.strip()

    if not query:

        return {
            "tool": "web_search",
            "query": "",
            "results": []
        }

    encoded_query = urllib.parse.quote_plus(
        query
    )

    url = (
        "https://html.duckduckgo.com/html/?q="
        + encoded_query
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/154.0 Safari/537.36"
            )
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            html = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        parser = SearchResultParser()

        parser.feed(html)

        return {
            "tool": "web_search",
            "query": query,
            "results": parser.results[
                :max_results
            ]
        }

    except Exception as error:

        return {
            "tool": "web_search",
            "query": query,
            "results": [],
            "error": str(error)
        }


def prepare_search(request):

    request = request.strip()

    prefixes = [
        "search the web for",
        "search online for",
        "search the internet for",
        "look up",
        "find online",
    ]

    lower_request = request.lower()

    for prefix in prefixes:

        if lower_request.startswith(prefix):

            query = request[
                len(prefix):
            ].strip()

            if query.lower().startswith("the "):

                query = query[4:].strip()

            return search_web(query)

    return search_web(request)


if __name__ == "__main__":

    result = search_web(
        "What is Python?",
        5
    )

    print()

    print("SEARCH RESULTS:")

    for item in result["results"]:

        print()

        print("TITLE:")
        print(item["title"])

        print("URL:")
        print(item["url"])