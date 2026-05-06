import httpx
from bs4 import BeautifulSoup


BASE_URL = "https://quotes.toscrape.com"


def crawl_quotes(max_pages: int = 10):
    results = []
    page = 1

    while page <= max_pages:
        url = f"{BASE_URL}/page/{page}/"
        response = httpx.get(url, timeout=10)

        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.text, "html.parser")
        quote_blocks = soup.select(".quote")

        if not quote_blocks:
            break

        for block in quote_blocks:
            # None 방어 — 요소가 없으면 해당 명언 건너뜀
            text_el = block.select_one(".text")
            author_el = block.select_one(".author")

            if not text_el or not author_el:
                continue

            # 유니코드 따옴표(\u201c \u201d) 및 일반 따옴표 제거
            text = text_el.get_text(strip=True).strip('\u201c\u201d\u2018\u2019"\'')
            author = author_el.get_text(strip=True)
            tags = [tag.get_text(strip=True) for tag in block.select(".tags .tag")]

            results.append({
                "text": text,
                "author": author,
                "tags": tags,
                "word_count": len(text.split()),
                "char_count": len(text)
            })

        page += 1

    return results