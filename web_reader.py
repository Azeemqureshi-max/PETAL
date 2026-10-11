import gzip
import urllib.request
from html.parser import HTMLParser


class PageTextParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.text_parts = []

        self.ignore_tags = {
            "script",
            "style",
            "noscript",
            "svg"
        }

        self.ignore_depth = 0

    def handle_starttag(self, tag, attrs):

        if tag in self.ignore_tags:
            self.ignore_depth += 1

    def handle_endtag(self, tag):

        if tag in self.ignore_tags and self.ignore_depth > 0:
            self.ignore_depth -= 1

    def handle_data(self, data):

        if self.ignore_depth == 0:

            text = data.strip()

            if text:
                self.text_parts.append(text)


def read_web_page(url):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/154.0 Safari/537.36"
            ),
            "Accept-Encoding": "gzip"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            data = response.read()

            encoding = response.headers.get(
                "Content-Encoding",
                ""
            ).lower()

        # Decompress gzip response.
        if encoding == "gzip":

            data = gzip.decompress(data)

        html = data.decode(
            "utf-8",
            errors="ignore"
        )

        parser = PageTextParser()
        parser.feed(html)

        text = " ".join(parser.text_parts)

        return text[:12000]

    except Exception as error:

        return f"[WEB READER ERROR] {error}"


if __name__ == "__main__":

    url = "https://www.python.org/"

    text = read_web_page(url)

    print(text[:3000])