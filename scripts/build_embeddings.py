from sentence_transformers import SentenceTransformer

from core.database import init_db, get_connection
from analyzers.similarity import serialize_vector


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def build_embeddings():
    init_db()

    print("임베딩 모델 로딩 중...")
    model = SentenceTransformer(MODEL_NAME)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT id, text
    FROM quotes
    ORDER BY id
    """)

    quotes = cur.fetchall()

    saved = 0

    for quote in quotes:
        quote_id = quote["id"]
        text = quote["text"]

        cur.execute("""
        SELECT quote_id
        FROM embeddings
        WHERE quote_id = ?
        """, (quote_id,))

        exists = cur.fetchone()

        if exists:
            continue

        vector = model.encode(text)
        vector_blob = serialize_vector(vector)

        cur.execute("""
        INSERT OR REPLACE INTO embeddings (
            quote_id,
            vector,
            model_name
        )
        VALUES (?, ?, ?)
        """, (quote_id, vector_blob, MODEL_NAME))

        saved += 1

        print(f"임베딩 저장: {quote_id}")

    conn.commit()
    conn.close()

    print("임베딩 생성 완료")
    print(f"전체 명언: {len(quotes)}개")
    print(f"새로 저장: {saved}개")


if __name__ == "__main__":
    build_embeddings()