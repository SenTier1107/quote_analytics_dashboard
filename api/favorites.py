from fastapi import APIRouter, HTTPException, Query
from collections import Counter
import re
import math

from core.database import get_connection
from analyzers.similarity import get_favorite_embedding_recommendations

router = APIRouter(prefix="/favorites", tags=["Favorites"])


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


def get_quote_tags(cur, quote_id: int):
    cur.execute(
        "SELECT tag FROM quote_tags WHERE quote_id = ?",
        (quote_id,)
    )
    return [row["tag"] for row in cur.fetchall()]


def row_to_quote(row, tags):
    return {
        "id": row["id"],
        "text": row["text"],
        "author": row["author"],
        "word_count": row["word_count"],
        "char_count": row["char_count"],
        "tags": tags
    }


@router.post("/{quote_id}")
def add_favorite(quote_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM quotes WHERE id = ?", (quote_id,))
    exists = cur.fetchone()

    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail="Quote not found")

    cur.execute(
        "INSERT OR IGNORE INTO favorites (quote_id) VALUES (?)",
        (quote_id,)
    )

    conn.commit()
    conn.close()

    return {"message": "Favorite added", "quote_id": quote_id}


@router.delete("/{quote_id}")
def remove_favorite(quote_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM favorites WHERE quote_id = ?", (quote_id,))

    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Favorite not found")

    conn.commit()
    conn.close()

    return {"message": "Favorite removed", "quote_id": quote_id}


@router.get("")
def get_favorites():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        q.id,
        q.text,
        q.author,
        q.word_count,
        q.char_count,
        GROUP_CONCAT(qt.tag) AS tags,
        f.added_at
    FROM favorites f
    JOIN quotes q ON f.quote_id = q.id
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    GROUP BY q.id
    ORDER BY f.added_at DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "text": row["text"],
            "author": row["author"],
            "word_count": row["word_count"],
            "char_count": row["char_count"],
            "tags": row["tags"].split(",") if row["tags"] else [],
            "added_at": row["added_at"]
        }
        for row in rows
    ]


@router.get("/profile")
def get_favorite_profile():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT q.id, q.text, q.author, q.word_count
    FROM favorites f
    JOIN quotes q ON f.quote_id = q.id
    """)

    fav_rows = cur.fetchall()

    if not fav_rows:
        conn.close()
        return {
            "message": "No favorites yet",
            "favorite_count": 0,
            "top_authors": [],
            "top_tags": [],
            "top_words": [],
            "avg_word_count": 0
        }

    author_counter = Counter()
    tag_counter = Counter()
    word_counter = Counter()
    total_word_count = 0

    for row in fav_rows:
        author_counter[row["author"]] += 1
        total_word_count += row["word_count"] or 0

        tags = get_quote_tags(cur, row["id"])
        tag_counter.update(tags)

        words = tokenize(row["text"])
        word_counter.update(words)

    conn.close()

    return {
        "favorite_count": len(fav_rows),
        "top_authors": author_counter.most_common(5),
        "top_tags": tag_counter.most_common(10),
        "top_words": word_counter.most_common(10),
        "avg_word_count": round(total_word_count / len(fav_rows), 2)
    }


@router.get("/recommend")
def recommend_quotes(limit: int = Query(default=5, ge=1, le=20)):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT q.id, q.text, q.author, q.word_count, q.char_count
    FROM favorites f
    JOIN quotes q ON f.quote_id = q.id
    """)

    fav_rows = cur.fetchall()

    if not fav_rows:
        conn.close()
        return {
            "message": "No favorites yet. Add favorites first.",
            "recommendations": []
        }

    fav_ids = {row["id"] for row in fav_rows}
    fav_authors = Counter()
    fav_tags = Counter()
    fav_words = Counter()

    for row in fav_rows:
        fav_authors[row["author"]] += 1
        fav_tags.update(get_quote_tags(cur, row["id"]))
        fav_words.update(tokenize(row["text"]))

    cur.execute("""
    SELECT id, text, author, word_count, char_count
    FROM quotes
    """)

    all_quotes = cur.fetchall()

    recommendations = []

    for row in all_quotes:
        quote_id = row["id"]

        if quote_id in fav_ids:
            continue

        tags = get_quote_tags(cur, quote_id)
        words = tokenize(row["text"])

        author_score = 5 if row["author"] in fav_authors else 0
        tag_score = sum(3 for tag in tags if tag in fav_tags)
        word_score = sum(1 for word in words if word in fav_words)

        raw_score = author_score + tag_score + word_score

        if raw_score <= 0:
            continue

        score = min(100, math.floor(raw_score * 8))

        reasons = []

        if author_score > 0:
            reasons.append(f"좋아하는 저자 '{row['author']}'와 일치")

        matched_tags = [tag for tag in tags if tag in fav_tags]
        if matched_tags:
            reasons.append(f"선호 태그 일치: {', '.join(matched_tags[:3])}")

        matched_words = [word for word in words if word in fav_words]
        if matched_words:
            reasons.append(f"선호 단어 포함: {', '.join(matched_words[:3])}")

        recommendations.append({
            "id": quote_id,
            "text": row["text"],
            "author": row["author"],
            "tags": tags,
            "score": score,
            "reason": " / ".join(reasons)
        })

    conn.close()

    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return {
        "message": "Recommendations generated",
        "recommendations": recommendations[:limit]
    }

@router.get("/recommend/embedding")
def recommend_quotes_by_embedding(limit: int = Query(default=5, ge=1, le=20)):
    recommendations = get_favorite_embedding_recommendations(top_k=limit)

    if not recommendations:
        return {
            "message": "No embedding recommendations found. Add favorites and build embeddings first.",
            "recommendations": []
        }

    return {
        "message": "Embedding recommendations generated",
        "recommendations": recommendations
    }