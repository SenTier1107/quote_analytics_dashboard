from fastapi import APIRouter, HTTPException
from core.database import get_connection
from analyzers.tfidf import get_author_signature_words

router = APIRouter(prefix="/authors", tags=["Authors"])


@router.get("")
def get_authors():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        a.name,
        a.birth_year,
        a.death_year,
        a.century,
        a.occupation,
        a.occupation_group,
        a.description,
        a.image_url,
        COUNT(q.id) AS quote_count
    FROM authors a
    LEFT JOIN quotes q ON a.name = q.author
    GROUP BY a.name
    ORDER BY a.name
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "name": row["name"],
            "birth_year": row["birth_year"],
            "death_year": row["death_year"],
            "century": row["century"],
            "occupation": row["occupation"],
            "occupation_group": row["occupation_group"],
            "description": row["description"],
            "image_url": row["image_url"],
            "quote_count": row["quote_count"]
        }
        for row in rows
    ]


@router.get("/{author_name}")
def get_author_detail(author_name: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
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
    FROM authors
    WHERE name = ?
    """, (author_name,))

    author = cur.fetchone()

    if not author:
        conn.close()
        raise HTTPException(status_code=404, detail="Author not found")

    cur.execute("""
    SELECT
        q.id,
        q.text,
        q.word_count,
        q.char_count,
        GROUP_CONCAT(qt.tag) AS tags
    FROM quotes q
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    WHERE q.author = ?
    GROUP BY q.id
    ORDER BY q.id
    """, (author_name,))

    quote_rows = cur.fetchall()

    cur.execute("""
    SELECT AVG(word_count) AS avg_word_count
    FROM quotes
    WHERE author = ?
    """, (author_name,))

    avg_word_count = cur.fetchone()["avg_word_count"] or 0

    cur.execute("""
    SELECT qt.tag, COUNT(*) AS count
    FROM quotes q
    JOIN quote_tags qt ON q.id = qt.quote_id
    WHERE q.author = ?
    GROUP BY qt.tag
    ORDER BY count DESC
    LIMIT 10
    """, (author_name,))

    tag_rows = cur.fetchall()

    conn.close()

    return {
        "name": author["name"],
        "birth_year": author["birth_year"],
        "death_year": author["death_year"],
        "century": author["century"],
        "nationality": author["nationality"],
        "occupation": author["occupation"],
        "occupation_group": author["occupation_group"],
        "description": author["description"],
        "summary": author["summary"],
        "image_url": author["image_url"],
        "wiki_url": author["wiki_url"],
        "quote_count": len(quote_rows),
        "avg_word_count": round(avg_word_count, 2),
        "top_tags": [
            {
                "tag": row["tag"],
                "count": row["count"]
            }
            for row in tag_rows
        ],
        "quotes": [
            {
                "id": row["id"],
                "text": row["text"],
                "word_count": row["word_count"],
                "char_count": row["char_count"],
                "tags": row["tags"].split(",") if row["tags"] else []
            }
            for row in quote_rows
        ]
    }

@router.get("/{author_name}/signature")
def get_author_signature(author_name: str):
    words = get_author_signature_words(author_name, top_n=10)

    if not words:
        raise HTTPException(status_code=404, detail="Signature words not found")

    return {
        "author": author_name,
        "signature_words": [
            {
                "word": word,
                "score": round(score, 4)
            }
            for word, score in words
        ]
    }