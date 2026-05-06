from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from core.database import get_connection  # get_next_quote_id 제거
from core.models import QuoteCreate, QuoteUpdate
from analyzers.similarity import get_similar_quotes
from visualizers.card_image import create_quote_card

router = APIRouter(prefix="/quotes", tags=["Quotes"])


def row_to_quote(row):
    return {
        "id": row["id"],
        "text": row["text"],
        "author": row["author"],
        "word_count": row["word_count"],
        "char_count": row["char_count"],
        "tags": row["tags"].split(",") if row["tags"] else []
    }


@router.get("/random")
def get_random_quote():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        q.id,
        q.text,
        q.author,
        q.word_count,
        q.char_count,
        GROUP_CONCAT(qt.tag) AS tags
    FROM quotes q
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    GROUP BY q.id
    ORDER BY RANDOM()
    LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Quote not found")

    return row_to_quote(row)


@router.get("/today")
def get_today_quote():
    from datetime import date

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        q.id,
        q.text,
        q.author,
        q.word_count,
        q.char_count,
        GROUP_CONCAT(qt.tag) AS tags
    FROM quotes q
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    GROUP BY q.id
    ORDER BY q.id
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="Quote not found")

    index = date.today().toordinal() % len(rows)

    return row_to_quote(rows[index])


@router.get("/{quote_id}/similar")
def get_quote_similar(quote_id: int, limit: int = Query(default=5, ge=1, le=20)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM quotes WHERE id = ?", (quote_id,))
    exists = cur.fetchone()
    conn.close()

    if not exists:
        raise HTTPException(status_code=404, detail="Quote not found")

    results = get_similar_quotes(quote_id, top_k=limit)

    if not results:
        return {
            "message": "No similar quotes found. Build embeddings first.",
            "quotes": []
        }

    return {
        "quote_id": quote_id,
        "similar_quotes": results
    }


@router.get("/{quote_id}/card")
def get_quote_card(quote_id: int):
    path = create_quote_card(quote_id)

    if not path:
        raise HTTPException(status_code=404, detail="Quote not found")

    return FileResponse(
        path,
        media_type="image/png",
        filename=f"quote_{quote_id}.png"
    )


@router.get("")
def get_quotes(
    keyword: str | None = Query(default=None),
    author: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT
        q.id,
        q.text,
        q.author,
        q.word_count,
        q.char_count,
        GROUP_CONCAT(qt.tag) AS tags
    FROM quotes q
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    WHERE 1 = 1
    """

    params = []

    if keyword:
        query += " AND q.text LIKE ?"
        params.append(f"%{keyword}%")

    if author:
        query += " AND q.author LIKE ?"
        params.append(f"%{author}%")

    if tag:
        query += """
        AND q.id IN (
            SELECT quote_id FROM quote_tags WHERE tag LIKE ?
        )
        """
        params.append(f"%{tag}%")

    query += """
    GROUP BY q.id
    ORDER BY q.id DESC
    LIMIT ? OFFSET ?
    """

    params.extend([limit, offset])

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [row_to_quote(row) for row in rows]


@router.get("/{quote_id}")
def get_quote(quote_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        q.id,
        q.text,
        q.author,
        q.word_count,
        q.char_count,
        GROUP_CONCAT(qt.tag) AS tags
    FROM quotes q
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    WHERE q.id = ?
    GROUP BY q.id
    """, (quote_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Quote not found")

    return row_to_quote(row)


@router.post("")
def create_quote(quote: QuoteCreate):
    conn = get_connection()
    cur = conn.cursor()

    word_count = len(quote.text.split())
    char_count = len(quote.text)

    # 삭제된 ID 재사용 — 현재 MAX(id) + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM quotes")
    next_id = cur.fetchone()["next_id"]

    cur.execute("""
    INSERT INTO quotes (id, text, author, word_count, char_count)
    VALUES (?, ?, ?, ?, ?)
    """, (next_id, quote.text, quote.author, word_count, char_count))

    for tag in quote.tags:
        cur.execute("INSERT OR IGNORE INTO quote_tags (quote_id, tag) VALUES (?, ?)", (next_id, tag))

    conn.commit()
    conn.close()

    return {"message": "Quote created", "id": next_id}

@router.put("/{quote_id}")
def update_quote(quote_id: int, quote: QuoteUpdate):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM quotes WHERE id = ?", (quote_id,))
    exists = cur.fetchone()

    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail="Quote not found")

    if quote.text is not None:
        cur.execute("""
        UPDATE quotes
        SET text = ?, word_count = ?, char_count = ?
        WHERE id = ?
        """, (
            quote.text,
            len(quote.text.split()),
            len(quote.text),
            quote_id
        ))

    if quote.author is not None:
        cur.execute("""
        UPDATE quotes
        SET author = ?
        WHERE id = ?
        """, (quote.author, quote_id))

    if quote.tags is not None:
        cur.execute("DELETE FROM quote_tags WHERE quote_id = ?", (quote_id,))

        for tag in quote.tags:
            cur.execute("""
            INSERT OR IGNORE INTO quote_tags (quote_id, tag)
            VALUES (?, ?)
            """, (quote_id, tag))

    conn.commit()
    conn.close()

    return {"message": "Quote updated"}


@router.delete("/{quote_id}")
def delete_quote(quote_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM quotes WHERE id = ?", (quote_id,))
    exists = cur.fetchone()

    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail="Quote not found")

    cur.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))

    conn.commit()
    conn.close()

    return {"message": "Quote deleted"}