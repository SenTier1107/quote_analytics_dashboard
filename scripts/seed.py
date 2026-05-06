from core.database import init_db, get_connection
from crawler.quotes_crawler import crawl_quotes


def seed_quotes():
    init_db()
    quotes = crawl_quotes(max_pages=10)

    conn = get_connection()
    cur = conn.cursor()
    inserted = 0

    for quote in quotes:
        cur.execute(
            "SELECT id FROM quotes WHERE text = ? AND author = ?",
            (quote["text"], quote["author"])
        )
        if cur.fetchone():
            continue

        # 삭제된 ID 재사용
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM quotes")
        next_id = cur.fetchone()["next_id"]

        cur.execute("""
        INSERT INTO quotes (id, text, author, word_count, char_count)
        VALUES (?, ?, ?, ?, ?)
        """, (next_id, quote["text"], quote["author"], quote["word_count"], quote["char_count"]))

        for tag in quote["tags"]:
            cur.execute("INSERT OR IGNORE INTO quote_tags (quote_id, tag) VALUES (?, ?)", (next_id, tag))

        inserted += 1

    conn.commit()
    conn.close()

    print(f"수집 완료: {len(quotes)}개")
    print(f"새로 저장된 명언: {inserted}개")


if __name__ == "__main__":
    seed_quotes()