import re
from urllib.parse import quote

import httpx


WIKI_API_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"

HEADERS = {
    "User-Agent": "QuoteInsightDashboard/0.1 (student-project; contact@example.com)"
}


def extract_birth_death_years(description, summary):
    """
    Wikipedia description/summary에서 출생년도와 사망년도를 최대한 정확하게 추출한다.

    우선순위:
    1. description의 (1904–1991), (1869-1951) 형태
    2. born 1948 형태
    3. summary의 1879 – 1955 형태
    4. 마지막 fallback: summary 안의 연도 2개
    """
    description = description or ""
    summary = summary or ""

    combined = f"{description} {summary}"

    # 1. 괄호 안 연도 범위: (1904–1991), (1904-1991)
    range_patterns = [
        r"\((?:c\.\s*)?(\d{4})\s*[–—-]\s*(\d{4})\)",
        r"\((?:c\.\s*)?(\d{4})\s*-\s*(\d{4})\)",
    ]

    for pattern in range_patterns:
        match = re.search(pattern, description)
        if match:
            return int(match.group(1)), int(match.group(2))

    # 2. description의 born 1948, born 31 July 1965
    born_match = re.search(r"\bborn\b[^0-9]*(\d{4})", description, re.IGNORECASE)
    if born_match:
        return int(born_match.group(1)), None

    # 3. summary 안에서 연도 범위 찾기
    for pattern in range_patterns:
        match = re.search(pattern, summary)
        if match:
            return int(match.group(1)), int(match.group(2))

    # 4. summary에 "1879 – 1955" 형태가 괄호 없이 있는 경우
    match = re.search(r"\b(\d{4})\s*[–—-]\s*(\d{4})\b", combined)
    if match:
        return int(match.group(1)), int(match.group(2))

    # 5. born 표현이 summary에 있는 경우
    born_match = re.search(r"\bborn\b[^0-9]*(\d{4})", summary, re.IGNORECASE)
    if born_match:
        return int(born_match.group(1)), None

    # 6. 마지막 fallback: 전체 텍스트에서 연도 2개 추출
    years = re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", combined)
    years = [int(year) for year in years]

    if not years:
        return None, None

    birth_year = years[0]
    death_year = years[1] if len(years) >= 2 and years[1] > birth_year else None

    return birth_year, death_year


def get_century_from_year(year):
    if not year:
        return None

    century = (year - 1) // 100 + 1

    if century == 18:
        return "18세기"
    if century == 19:
        return "19세기"
    if century == 20:
        return "20세기"
    if century == 21:
        return "21세기"

    return f"{century}세기"


def guess_occupation_group(description, summary):
    text = f"{description or ''} {summary or ''}".lower()

    if any(word in text for word in ["writer", "novelist", "poet", "author", "playwright", "essayist"]):
        return "Writer"

    if any(word in text for word in ["scientist", "physicist", "mathematician", "chemist", "biologist", "inventor"]):
        return "Scientist"

    if any(word in text for word in ["actor", "actress", "film", "director", "musician", "singer", "comedian", "cartoonist"]):
        return "Artist"

    if any(word in text for word in ["politician", "president", "prime minister", "statesman", "activist", "minister"]):
        return "Politician"

    if any(word in text for word in ["philosopher", "theologian"]):
        return "Philosopher"

    if any(word in text for word in ["entrepreneur", "businessman", "businesswoman"]):
        return "Entrepreneur"

    return "Other"


def fetch_author_info(author_name):
    page_title = author_name.replace(" ", "_")
    encoded_title = quote(page_title)
    url = f"{WIKI_API_URL}/{encoded_title}"

    try:
        response = httpx.get(
            url,
            headers=HEADERS,
            timeout=15,
            follow_redirects=True
        )
    except httpx.RequestError as e:
        print(f"[요청 오류] {author_name}: {e}")
        return None

    if response.status_code != 200:
        print(f"[상태 오류] {author_name}: status={response.status_code}, url={url}")
        return None

    data = response.json()

    description = data.get("description")
    summary = data.get("extract")

    image_url = None
    if data.get("thumbnail"):
        image_url = data["thumbnail"].get("source")

    wiki_url = None
    if data.get("content_urls"):
        wiki_url = data["content_urls"].get("desktop", {}).get("page")

    birth_year, death_year = extract_birth_death_years(description, summary)
    century = get_century_from_year(birth_year)
    occupation_group = guess_occupation_group(description, summary)

    return {
        "name": author_name,
        "birth_year": birth_year,
        "death_year": death_year,
        "century": century,
        "nationality": None,
        "occupation": description,
        "occupation_group": occupation_group,
        "description": description,
        "summary": summary,
        "image_url": image_url,
        "wiki_url": wiki_url
    }