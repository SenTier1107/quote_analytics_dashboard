import numpy as np
from core.database import get_connection


def serialize_vector(vector):
    return np.asarray(vector, dtype=np.float32).tobytes()


def deserialize_vector(blob):
    return np.frombuffer(blob, dtype=np.float32)


def cosine_similarity(vec1, vec2):
    vec1 = np.asarray(vec1, dtype=np.float32)
    vec2 = np.asarray(vec2, dtype=np.float32)

    denom = np.linalg.norm(vec1) * np.linalg.norm(vec2)

    if denom == 0:
        return 0.0

    return float(np.dot(vec1, vec2) / denom)


def get_quote_vector(cur, quote_id):
    cur.execute("""
    SELECT vector
    FROM embeddings
    WHERE quote_id = ?
    """, (quote_id,))

    row = cur.fetchone()

    if not row:
        return None

    return deserialize_vector(row["vector"])


def get_similar_quotes(quote_id, top_k=5):
    conn = get_connection()
    cur = conn.cursor()

    base_vector = get_quote_vector(cur, quote_id)

    if base_vector is None:
        conn.close()
        return []

    cur.execute("""
    SELECT
        q.id,
        q.text,
        q.author,
        q.word_count,
        q.char_count,
        e.vector
    FROM quotes q
    JOIN embeddings e ON q.id = e.quote_id
    WHERE q.id != ?
    """, (quote_id,))

    rows = cur.fetchall()

    results = []

    for row in rows:
        target_vector = deserialize_vector(row["vector"])
        score = cosine_similarity(base_vector, target_vector)

        cur.execute("""
        SELECT tag
        FROM quote_tags
        WHERE quote_id = ?
        """, (row["id"],))

        tags = [tag_row["tag"] for tag_row in cur.fetchall()]

        results.append({
            "id": row["id"],
            "text": row["text"],
            "author": row["author"],
            "word_count": row["word_count"],
            "char_count": row["char_count"],
            "tags": tags,
            "similarity": round(score, 4)
        })

    conn.close()

    results.sort(key=lambda x: x["similarity"], reverse=True)

    return results[:int(top_k)]


def get_favorite_embedding_recommendations(top_k=5):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT q.id, e.vector
    FROM favorites f
    JOIN quotes q ON f.quote_id = q.id
    JOIN embeddings e ON q.id = e.quote_id
    """)

    fav_rows = cur.fetchall()

    if not fav_rows:
        conn.close()
        return []

    fav_ids = {row["id"] for row in fav_rows}
    fav_vectors = [deserialize_vector(row["vector"]) for row in fav_rows]

    taste_vector = np.mean(fav_vectors, axis=0)

    cur.execute("""
    SELECT
        q.id,
        q.text,
        q.author,
        q.word_count,
        q.char_count,
        e.vector
    FROM quotes q
    JOIN embeddings e ON q.id = e.quote_id
    """)

    rows = cur.fetchall()

    results = []

    for row in rows:
        if row["id"] in fav_ids:
            continue

        vector = deserialize_vector(row["vector"])
        score = cosine_similarity(taste_vector, vector)

        cur.execute("""
        SELECT tag
        FROM quote_tags
        WHERE quote_id = ?
        """, (row["id"],))

        tags = [tag_row["tag"] for tag_row in cur.fetchall()]

        results.append({
            "id": row["id"],
            "text": row["text"],
            "author": row["author"],
            "tags": tags,
            "score": round(score * 100, 2),
            "reason": "즐겨찾기한 명언들과 의미적으로 유사합니다."
        })

    conn.close()

    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:int(top_k)]