import time

from core.database import init_db, get_connection
from crawler.wiki_enricher import fetch_author_info


def get_unique_authors():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT DISTINCT author
    FROM quotes
    ORDER BY author
    """)

    authors = [row["author"] for row in cur.fetchall()]

    conn.close()

    return authors


def seed_authors():
    init_db()

    authors = get_unique_authors()

    conn = get_connection()
    cur = conn.cursor()

    saved = 0
    failed = 0

    for author in authors:
        print(f"수집 중: {author}")

        info = fetch_author_info(author)

        time.sleep(1)

        if not info:
            print(f"실패: {author}")
            failed += 1
            continue

        cur.execute("""
        INSERT OR REPLACE INTO authors (
            name,
            birth_year,
            death_year,
            century,
            nationality,
            occupation,
            occupation_group,
            description,
            summary,
            image_url,
            wiki_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            info["name"],
            info["birth_year"],
            info["death_year"],
            info["century"],
            info["nationality"],
            info["occupation"],
            info["occupation_group"],
            info["description"],
            info["summary"],
            info["image_url"],
            info["wiki_url"]
        ))

        conn.commit()

        print(f"저장/업데이트: {author}")
        saved += 1

    conn.close()

    print("저자 정보 수집 완료")
    print(f"전체 저자: {len(authors)}명")
    print(f"저장/업데이트: {saved}명")
    print(f"실패: {failed}명")


if __name__ == "__main__":
    seed_authors()