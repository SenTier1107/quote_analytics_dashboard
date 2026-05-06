from fastapi import APIRouter, Query
from collections import Counter
import re

from core.database import get_connection
from analyzers.tfidf import (
    get_occupation_group_signature_words,
    get_all_occupation_groups
)
from analyzers.network import get_tag_cooccurrence_pairs

router = APIRouter(prefix="/stats", tags=["Stats"])


STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "to", "of", "in", "on", "for", "with", "as", "by", "at", "from",
    "it", "this", "that", "you", "your", "i", "me", "my", "we", "our",
    "they", "them", "their", "he", "she", "his", "her", "be", "been",
    "have", "has", "had", "do", "does", "did", "not", "no", "so",
    "if", "then", "than", "too", "very", "can", "will", "just"
}


def tokenize(text: str):
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return [
        word for word in words
        if word not in STOPWORDS and len(word) >= 3
    ]


@router.get("/summary")
def get_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS total_quotes FROM quotes")
    total_quotes = cur.fetchone()["total_quotes"]

    cur.execute("SELECT COUNT(DISTINCT author) AS total_authors FROM quotes")
    total_authors = cur.fetchone()["total_authors"]

    cur.execute("SELECT COUNT(DISTINCT tag) AS total_tags FROM quote_tags")
    total_tags = cur.fetchone()["total_tags"]

    cur.execute("SELECT AVG(word_count) AS avg_word_count FROM quotes")
    avg_word_count = cur.fetchone()["avg_word_count"] or 0

    conn.close()

    return {
        "total_quotes": total_quotes,
        "total_authors": total_authors,
        "total_tags": total_tags,
        "avg_word_count": round(avg_word_count, 2)
    }


@router.get("/word-count")
def get_word_count(limit: int = Query(default=20, ge=1, le=100)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT text FROM quotes")
    rows = cur.fetchall()
    conn.close()

    counter = Counter()

    for row in rows:
        counter.update(tokenize(row["text"]))

    return [
        {"word": word, "count": count}
        for word, count in counter.most_common(limit)
    ]


@router.get("/length-distribution")
def get_length_distribution():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT id, text, author, word_count
    FROM quotes
    ORDER BY word_count ASC
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "text": row["text"],
            "author": row["author"],
            "word_count": row["word_count"]
        }
        for row in rows
    ]

@router.get("/occupation-groups")
def get_occupation_groups():
    return {
        "occupation_groups": get_all_occupation_groups()
    }


@router.get("/occupation-signature")
def get_occupation_signature(group: str, limit: int = Query(default=10, ge=1, le=30)):
    words = get_occupation_group_signature_words(group, top_n=limit)

    return {
        "group": group,
        "signature_words": [
            {
                "word": word,
                "score": round(score, 4)
            }
            for word, score in words
        ]
    }

@router.get("/by-dimension")
def get_stats_by_dimension(dim: str = Query(default="occupation_group")):
    conn = get_connection()
    cur = conn.cursor()

    if dim == "century":
        cur.execute("""
        SELECT COALESCE(a.century, '정보 없음') AS label, COUNT(q.id) AS quote_count
        FROM quotes q
        LEFT JOIN authors a ON q.author = a.name
        GROUP BY label
        ORDER BY quote_count DESC
        """)
    else:
        cur.execute("""
        SELECT COALESCE(a.occupation_group, 'Other') AS label, COUNT(q.id) AS quote_count
        FROM quotes q
        LEFT JOIN authors a ON q.author = a.name
        GROUP BY label
        ORDER BY quote_count DESC
        """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "dimension": dim,
            "label": row["label"],
            "quote_count": row["quote_count"]
        }
        for row in rows
    ]


@router.get("/tag-cooccurrence")
def get_tag_cooccurrence(limit: int = Query(default=30, ge=1, le=100)):
    return get_tag_cooccurrence_pairs(limit=limit)


@router.get("/occupation-tag-heatmap")
def get_occupation_tag_heatmap_data(top_tags: int = Query(default=10, ge=5, le=30)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT tag, COUNT(*) AS count
    FROM quote_tags
    GROUP BY tag
    ORDER BY count DESC
    LIMIT ?
    """, (int(top_tags),))

    tag_rows = cur.fetchall()
    tags = [row["tag"] for row in tag_rows]

    cur.execute("""
    SELECT DISTINCT COALESCE(occupation_group, 'Other') AS group_name
    FROM authors
    ORDER BY group_name
    """)

    groups = [row["group_name"] for row in cur.fetchall()]

    data = []

    for group in groups:
        for tag in tags:
            cur.execute("""
            SELECT COUNT(*) AS count
            FROM quotes q
            JOIN authors a ON q.author = a.name
            JOIN quote_tags qt ON q.id = qt.quote_id
            WHERE COALESCE(a.occupation_group, 'Other') = ?
              AND qt.tag = ?
            """, (group, tag))

            data.append({
                "occupation_group": group,
                "tag": tag,
                "count": cur.fetchone()["count"]
            })

    conn.close()

    return {
        "groups": groups,
        "tags": tags,
        "data": data
    }