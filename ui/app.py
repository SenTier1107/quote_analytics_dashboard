import gradio as gr
from collections import Counter
import re

from core.database import get_connection
from visualizers.charts import (
    create_wordcloud_figure,
    create_word_count_bar,
    create_length_histogram,
    create_tag_bar_chart,
    create_dimension_bar_chart,
)
from analyzers.tfidf import (
    get_author_signature_words,
    get_occupation_group_signature_words,
    get_all_occupation_groups
)
from analyzers.similarity import get_favorite_embedding_recommendations
from visualizers.network_plot import create_tag_network_figure



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


def parse_tags(tag_text):
    if not tag_text:
        return []
    return [tag.strip() for tag in tag_text.split(",") if tag.strip()]





def get_kpi_cards():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS v FROM quotes")
    total_quotes = cur.fetchone()["v"]
    cur.execute("SELECT COUNT(DISTINCT author) AS v FROM quotes")
    total_authors = cur.fetchone()["v"]
    cur.execute("SELECT COUNT(DISTINCT tag) AS v FROM quote_tags")
    total_tags = cur.fetchone()["v"]
    cur.execute("SELECT AVG(word_count) AS v FROM quotes")
    avg_words = cur.fetchone()["v"] or 0
    cur.execute("SELECT COUNT(*) AS v FROM favorites")
    favorites = cur.fetchone()["v"]
    conn.close()

    # 주황 계열 그라데이션
    gradients = [
        "linear-gradient(135deg, #f7971e, #e65c00)",
        "linear-gradient(135deg, #f9a825, #f57c00)",
        "linear-gradient(135deg, #ff8f00, #e65c00)",
        "linear-gradient(135deg, #ffb300, #f57c00)",
        "linear-gradient(135deg, #ffa000, #e65c00)",
    ]

    cards = [
        ("📜", "전체 명언", f"{total_quotes}개"),
        ("👤", "저자 수",   f"{total_authors}명"),
        ("🏷️", "태그 수",   f"{total_tags}개"),
        ("📏", "평균 단어", f"{avg_words:.1f}개"),
        ("⭐", "즐겨찾기", f"{favorites}개"),
    ]

    html = '<div style="display:flex; gap:12px; flex-wrap:wrap; margin:16px 0;">'
    for i, (icon, label, value) in enumerate(cards):
        html += f"""
        <div style="
            background: {gradients[i]};
            border-radius: 12px;
            padding: 20px 24px;
            color: white;
            text-align: center;
            flex: 1;
            min-width: 150px;
            box-shadow: 0 4px 15px rgba(230,92,0,0.3);
        ">
            <div style="font-size:28px; margin-bottom:6px;">{icon}</div>
            <div style="font-size:13px; opacity:0.85; margin-bottom:4px;">{label}</div>
            <div style="font-size:24px; font-weight:700;">{value}</div>
        </div>
        """
    html += "</div>"
    return html


def get_summary_text():
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

    cur.execute("SELECT COUNT(*) AS favorite_count FROM favorites")
    favorite_count = cur.fetchone()["favorite_count"]

    conn.close()

    return f"""
## 📊 Project Snapshot

| 지표 | 값 |
|---|---:|
| 전체 명언 수 | {total_quotes}개 |
| 저자 수 | {total_authors}명 |
| 고유 태그 수 | {total_tags}개 |
| 평균 단어 수 | {avg_word_count:.2f}개 |
| 즐겨찾기 수 | {favorite_count}개 |
"""


def get_overview_text():
    return """
## 📜 Quote Insight Dashboard

이 프로젝트는 `quotes.toscrape.com`의 명언 데이터를 수집한 뒤,  
FastAPI 기반 CRUD API와 Gradio 대시보드를 통해 데이터를 관리·분석·추천하는 시스템입니다.

### 🔁 데이터 흐름

`크롤링 → SQLite 저장 → FastAPI API → Gradio UI → 분석/추천`

### 🧩 주요 기능

| 영역 | 기능 |
|---|---|
| 데이터 수집 | 명언, 저자, 태그 크롤링 |
| API | FastAPI CRUD, Swagger 문서 |
| UI | Gradio 기반 통합 대시보드 |
| 분석 | 단어 빈도, 워드클라우드, 길이 분포, 태그 분석 |
| 저자 정보 | Wikipedia 메타데이터, 저자 프로필 |
| 고급 분석 | TF-IDF 시그니처 단어, 직업×태그 히트맵, 태그 네트워크 |
| 추천 | 즐겨찾기 기반 추천, 임베딩 기반 의미 추천 |
"""


def get_word_count_table(limit=20):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT text FROM quotes")
    rows = cur.fetchall()
    conn.close()
    counter = Counter()
    for row in rows:
        counter.update(tokenize(row["text"]))
    return [[word, count] for word, count in counter.most_common(int(limit))]


def get_length_distribution_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT id, text, author, word_count
    FROM quotes
    ORDER BY word_count DESC
    LIMIT 30
    """)
    rows = cur.fetchall()
    conn.close()
    return [[row["id"], row["author"], row["word_count"], row["text"]] for row in rows]


def search_quotes(quote_id=None, author=None, tag=None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT q.id, q.text, q.author, GROUP_CONCAT(qt.tag) AS tags
    FROM quotes q
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    WHERE 1 = 1
    """
    params = []

    if quote_id not in [None, ""]:
        query += " AND q.id = ?"
        params.append(int(quote_id))

    if author and str(author).strip():
        query += " AND q.author LIKE ?"
        params.append(f"%{str(author).strip()}%")

    if tag and str(tag).strip():
        query += " AND q.id IN (SELECT quote_id FROM quote_tags WHERE tag LIKE ?)"
        params.append(f"%{str(tag).strip()}%")

    query += " GROUP BY q.id ORDER BY q.id DESC LIMIT 50"

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [[row["id"], row["text"], row["author"], row["tags"] or ""] for row in rows]


def search_quotes_ui(quote_id, author, tag):
    # 숫자가 아닌 값 입력 시 에러 처리
    if quote_id and quote_id.strip() and not quote_id.strip().isdigit():
        return "❌ 명언 ID는 숫자만 입력해주세요.", []

    quote_id_int = int(quote_id.strip()) if quote_id and quote_id.strip().isdigit() else None

    # ID 단독으로 존재 여부 먼저 확인
    if quote_id_int is not None:
        id_exists = search_quotes(quote_id_int, None, None)
        if not id_exists:
            return f"❌ ID {quote_id_int}번 명언은 존재하지 않습니다.", []

    results = search_quotes(quote_id_int, author, tag)

    if not results:
        if quote_id_int is not None:
            return f"❌ ID {quote_id_int}번 명언은 존재하지만 선택한 조건(저자/태그)과 일치하지 않습니다.", []
        return "❌ 조건에 맞는 명언이 없습니다.", []

    return f"✅ 검색 결과 {len(results)}개를 찾았습니다.", results


def add_quote(text, author, tags):
    if not text or not author:
        return "❌ 명언과 저자는 반드시 입력해야 합니다.", search_quotes(None, None, None)

    tag_list = parse_tags(tags)
    conn = get_connection()
    cur = conn.cursor()

    # 삭제된 ID 재사용 — 현재 MAX(id) + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM quotes")
    next_id = cur.fetchone()["next_id"]

    cur.execute("""
    INSERT INTO quotes (id, text, author, word_count, char_count)
    VALUES (?, ?, ?, ?, ?)
    """, (next_id, text, author, len(text.split()), len(text)))

    for tag in tag_list:
        cur.execute("INSERT OR IGNORE INTO quote_tags (quote_id, tag) VALUES (?, ?)", (next_id, tag))

    conn.commit()
    conn.close()

    return f"✅ 새 명언이 추가되었습니다. ID: {next_id}", search_quotes(None, None, None)


def load_quote_for_edit(quote_id):
    if quote_id is None:
        return "", "", "", "❌ 수정할 ID를 입력하세요."

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT q.id, q.text, q.author, GROUP_CONCAT(qt.tag) AS tags
    FROM quotes q
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    WHERE q.id = ?
    GROUP BY q.id
    """, (int(quote_id),))
    row = cur.fetchone()
    conn.close()

    if not row:
        return "", "", "", "❌ 해당 ID의 명언을 찾을 수 없습니다."
    return row["text"], row["author"], row["tags"] or "", "✅ 수정할 명언을 불러왔습니다."


def update_quote(quote_id, text, author, tags):
    if quote_id is None:
        return "❌ 수정할 ID를 입력하세요.", search_quotes(None, None, None)
    if not text or not author:
        return "❌ 명언과 저자는 반드시 입력해야 합니다.", search_quotes(None, None, None)

    tag_list = parse_tags(tags)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM quotes WHERE id = ?", (int(quote_id),))
    if not cur.fetchone():
        conn.close()
        return "❌ 해당 ID의 명언을 찾을 수 없습니다.", search_quotes(None, None, None)

    cur.execute("""
    UPDATE quotes SET text = ?, author = ?, word_count = ?, char_count = ?
    WHERE id = ?
    """, (text, author, len(text.split()), len(text), int(quote_id)))

    cur.execute("DELETE FROM quote_tags WHERE quote_id = ?", (int(quote_id),))
    for tag in tag_list:
        cur.execute("INSERT OR IGNORE INTO quote_tags (quote_id, tag) VALUES (?, ?)", (int(quote_id), tag))

    conn.commit()
    conn.close()
    return f"✅ ID {int(quote_id)}번 명언이 수정되었습니다.", search_quotes(None, None, None)


def delete_quote(quote_id):
    if quote_id is None:
        return "❌ 삭제할 ID를 입력하세요.", search_quotes(None, None, None)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM quotes WHERE id = ?", (int(quote_id),))
    if not cur.fetchone():
        conn.close()
        return "❌ 해당 ID의 명언을 찾을 수 없습니다.", search_quotes(None, None, None)

    cur.execute("DELETE FROM quotes WHERE id = ?", (int(quote_id),))
    conn.commit()
    conn.close()
    return f"🗑️ ID {int(quote_id)}번 명언이 삭제되었습니다.", search_quotes(None, None, None)


def add_favorite_ui(quote_id):
    if quote_id is None:
        return "❌ 즐겨찾기할 명언 ID를 입력하세요.", get_favorites_table()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quotes WHERE id = ?", (int(quote_id),))
    if not cur.fetchone():
        conn.close()
        return "❌ 해당 ID의 명언을 찾을 수 없습니다.", get_favorites_table()

    cur.execute("INSERT OR IGNORE INTO favorites (quote_id) VALUES (?)", (int(quote_id),))
    conn.commit()
    conn.close()
    return f"⭐ ID {int(quote_id)}번 명언을 즐겨찾기에 추가했습니다.", get_favorites_table()


def remove_favorite_ui(quote_id):
    if quote_id is None:
        return "❌ 해제할 명언 ID를 입력하세요.", get_favorites_table()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM favorites WHERE quote_id = ?", (int(quote_id),))

    if cur.rowcount == 0:
        conn.close()
        return "❌ 해당 ID는 즐겨찾기에 없습니다.", get_favorites_table()

    conn.commit()
    conn.close()
    return f"⭐ ID {int(quote_id)}번 명언을 즐겨찾기에서 해제했습니다.", get_favorites_table()


def get_favorites_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT q.id, q.text, q.author, GROUP_CONCAT(qt.tag) AS tags
    FROM favorites f
    JOIN quotes q ON f.quote_id = q.id
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    GROUP BY q.id
    ORDER BY f.added_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [[row["id"], row["text"], row["author"], row["tags"] or ""] for row in rows]


def get_favorite_profile_text():
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
        return "## 🎯 내 취향 분석\n\n아직 즐겨찾기한 명언이 없습니다."

    author_counter = Counter()
    tag_counter = Counter()
    word_counter = Counter()
    total_word_count = 0

    for row in fav_rows:
        author_counter[row["author"]] += 1
        total_word_count += row["word_count"] or 0
        cur.execute("SELECT tag FROM quote_tags WHERE quote_id = ?", (row["id"],))
        tag_counter.update([r["tag"] for r in cur.fetchall()])
        word_counter.update(tokenize(row["text"]))

    conn.close()

    top_authors = ", ".join([f"{a}({c})" for a, c in author_counter.most_common(3)])
    top_tags    = ", ".join([f"{t}({c})" for t, c in tag_counter.most_common(5)])
    top_words   = ", ".join([f"{w}({c})" for w, c in word_counter.most_common(5)])
    avg_wc      = total_word_count / len(fav_rows)
    first_tag   = top_tags.split(",")[0].strip() if top_tags.strip() else "특정 주제"

    return f"""
## 🎯 내 취향 분석

| 항목 | 결과 |
|---|---|
| 즐겨찾기 수 | {len(fav_rows)}개 |
| 선호 저자 Top 3 | {top_authors} |
| 선호 태그 Top 5 | {top_tags} |
| 선호 단어 Top 5 | {top_words} |
| 평균 선호 길이 | {avg_wc:.2f} 단어 |

### 💬 한 줄 취향 진단
당신은 **{first_tag}** 계열의 명언에 관심이 높은 편입니다.
"""


def recommend_quotes_ui(limit=5):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT q.id, q.text, q.author
    FROM favorites f JOIN quotes q ON f.quote_id = q.id
    """)
    fav_rows = cur.fetchall()

    if not fav_rows:
        conn.close()
        return []

    fav_ids = {row["id"] for row in fav_rows}
    fav_authors = Counter()
    fav_tags    = Counter()
    fav_words   = Counter()

    for row in fav_rows:
        fav_authors[row["author"]] += 1
        cur.execute("SELECT tag FROM quote_tags WHERE quote_id = ?", (row["id"],))
        fav_tags.update([r["tag"] for r in cur.fetchall()])
        fav_words.update(tokenize(row["text"]))

    cur.execute("SELECT id, text, author, word_count FROM quotes")
    all_quotes = cur.fetchall()
    recommendations = []

    for row in all_quotes:
        if row["id"] in fav_ids:
            continue

        cur.execute("SELECT tag FROM quote_tags WHERE quote_id = ?", (row["id"],))
        tags  = [r["tag"] for r in cur.fetchall()]
        words = tokenize(row["text"])

        author_score = 5 if row["author"] in fav_authors else 0
        tag_score    = sum(3 for t in tags  if t in fav_tags)
        word_score   = sum(1 for w in words if w in fav_words)
        raw_score    = author_score + tag_score + word_score

        if raw_score <= 0:
            continue

        score   = min(100, raw_score * 8)
        reasons = []

        if author_score > 0:
            reasons.append(f"저자 일치: {row['author']}")
        matched_tags  = [t for t in tags  if t in fav_tags]
        matched_words = [w for w in words if w in fav_words]
        if matched_tags:
            reasons.append(f"태그 일치: {', '.join(matched_tags[:3])}")
        if matched_words:
            reasons.append(f"단어 유사: {', '.join(matched_words[:3])}")

        recommendations.append([
            row["id"], row["text"], row["author"],
            ", ".join(tags), score, " / ".join(reasons)
        ])

    conn.close()
    recommendations.sort(key=lambda x: x[4], reverse=True)
    return recommendations[:int(limit)]


def get_author_choices():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM authors ORDER BY name")
    authors = [row["name"] for row in cur.fetchall()]
    conn.close()
    return authors


def clean_description(description):
    if not description:
        return "정보 없음"
    description = re.sub(r"\s*\((?:c\.\s*)?\d{4}\s*[–—-]\s*\d{4}\)\s*$", "", description)
    description = re.sub(r"\s*\(born\s+.*?\d{4}\)\s*$", "", description, flags=re.IGNORECASE)
    return description.strip()


def get_author_profile(author_name):
    if not author_name:
        return "저자를 선택하세요.", "", [], [], []

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT name, birth_year, death_year, century, occupation,
           occupation_group, description, summary, image_url, wiki_url
    FROM authors WHERE name = ?
    """, (author_name,))
    author = cur.fetchone()

    if not author:
        conn.close()
        return "해당 저자 정보를 찾을 수 없습니다.", "", [], [], []

    cur.execute("""
    SELECT q.id, q.text, q.word_count, GROUP_CONCAT(qt.tag) AS tags
    FROM quotes q
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    WHERE q.author = ? GROUP BY q.id ORDER BY q.id
    """, (author_name,))
    quote_rows = cur.fetchall()

    cur.execute("""
    SELECT qt.tag, COUNT(*) AS count
    FROM quotes q JOIN quote_tags qt ON q.id = qt.quote_id
    WHERE q.author = ?
    GROUP BY qt.tag ORDER BY count DESC LIMIT 10
    """, (author_name,))
    tag_rows = cur.fetchall()
    conn.close()

    # 왼쪽: 사진만
    image_md = ""
    if author["image_url"]:
        image_md = f"![{author['name']}]({author['image_url']})"

    # 오른쪽 상단: 기본 정보 테이블
    if author["birth_year"] and author["death_year"]:
        life = f'{author["birth_year"]}년 출생 / {author["death_year"]}년 사망'
    elif author["birth_year"]:
        life = f'{author["birth_year"]}년 출생'
    else:
        life = "정보 없음"

    info_md = f"""
## 👤 {author["name"]}

| 항목 | 내용 |
|---|---|
| 인물 설명 | {clean_description(author["occupation"])} |
| 분류 | {author["occupation_group"] or "Other"} |
| 출생 기준 시대 | {author["century"] or "정보 없음"} |
| 출생/사망 정보 | {life} |
| 수집된 명언 수 | {len(quote_rows)}개 |

### 소개
{author["summary"] or "Wikipedia 요약 정보가 없습니다."}

### Wikipedia
{author["wiki_url"] or "정보 없음"}
"""

    signature_words = get_author_signature_words(author_name, top_n=10)

    return (
        image_md,
        info_md,
        [[w, round(s, 4)] for w, s in signature_words],
        [[r["tag"], r["count"]] for r in tag_rows],
        [[r["id"], r["text"], r["word_count"], r["tags"] or ""] for r in quote_rows]
    )

def get_today_quote_text():
    from datetime import date

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT q.id, q.text, q.author, GROUP_CONCAT(qt.tag) AS tags
    FROM quotes q
    LEFT JOIN quote_tags qt ON q.id = qt.quote_id
    GROUP BY q.id ORDER BY q.id
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "오늘의 명언을 불러올 수 없습니다."

    row = rows[date.today().toordinal() % len(rows)]
    return f"""
## 💬 오늘의 명언

> {row["text"]}

— **{row["author"]}**

태그: {row["tags"] or "없음"}
"""





def embedding_recommend_ui(limit):
    results = get_favorite_embedding_recommendations(top_k=int(limit))
    return [
        [r["id"], r["text"], r["author"], ", ".join(r["tags"]), r["score"], r["reason"]]
        for r in results
    ]


def create_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# 명언 분석 · 추천 대시보드")
        gr.Markdown("명언 데이터를 수집하고, 분석하고, 개인 취향에 맞게 추천하는 통합 대시보드입니다.")

        with gr.Tab(" 홈"):
            # KPI 카드 — 전체 너비
            kpi_html = gr.HTML()
            demo.load(fn=get_kpi_cards, inputs=[], outputs=kpi_html)

            refresh_kpi_btn = gr.Button("통계 새로고침")
            refresh_kpi_btn.click(fn=get_kpi_cards, inputs=[], outputs=kpi_html)

            gr.Markdown("---")

            # 오늘의 명언 — 전체 너비로 상단 배치
            today_quote = gr.Markdown()
            demo.load(fn=get_today_quote_text, inputs=[], outputs=today_quote)

            gr.Markdown("---")

            # 프로젝트 소개 — 전체 너비
            overview = gr.Markdown()
            demo.load(fn=get_overview_text, inputs=[], outputs=overview)

        with gr.Tab(" 명언 검색 및 관리"):
            gr.Markdown("## 🔎 명언 검색")
            gr.Markdown("ID로 특정 명언을 찾거나, 저자 이름 자동완성 목록에서 선택해 검색할 수 있습니다.")

            with gr.Row():
                quote_id_search = gr.Textbox(label="명언 ID", placeholder="예: 1, 2, 3", value="")
                author = gr.Dropdown(
                    choices=get_author_choices(), value=None, label="저자",
                    filterable=True, allow_custom_value=True, interactive=True
                )
                tag = gr.Textbox(label="태그", placeholder="예: life, love, inspirational")

            with gr.Row():
                search_btn       = gr.Button("검색", variant="primary")
                reset_search_btn = gr.Button("검색 조건 초기화")

            search_message = gr.Markdown()
            output = gr.Dataframe(headers=["ID", "명언", "저자", "태그"], label="검색 결과", wrap=True)

            search_btn.click(
                fn=search_quotes_ui,
                inputs=[quote_id_search, author, tag],
                outputs=[search_message, output]
            )
            reset_search_btn.click(
                fn=lambda: (None, None, "", "✅ 검색 조건을 초기화했습니다.", search_quotes(None, None, None)),
                inputs=[],
                outputs=[quote_id_search, author, tag, search_message, output]
            )
            demo.load(fn=lambda: search_quotes(None, None, None), inputs=[], outputs=output)

            gr.Markdown("---")
            gr.Markdown("## 🛠️ 명언 관리")

            with gr.Accordion("➕ 새 명언 추가", open=False):
                add_text   = gr.Textbox(label="명언", lines=3)
                add_author = gr.Textbox(label="저자")
                add_tags   = gr.Textbox(label="태그", placeholder="예: life, love, inspiration")
                add_btn    = gr.Button("명언 추가", variant="primary")
                add_message = gr.Markdown()
                add_btn.click(fn=add_quote, inputs=[add_text, add_author, add_tags], outputs=[add_message, output])

            with gr.Accordion("✏️ 명언 수정", open=False):
                edit_id     = gr.Number(label="수정할 명언 ID", precision=0)
                load_btn    = gr.Button("ID로 불러오기")
                edit_text   = gr.Textbox(label="수정할 명언", lines=3)
                edit_author = gr.Textbox(label="수정할 저자")
                edit_tags   = gr.Textbox(label="수정할 태그", placeholder="예: life, love, inspiration")
                edit_message = gr.Markdown()
                update_btn  = gr.Button("수정 저장", variant="primary")

                load_btn.click(fn=load_quote_for_edit, inputs=edit_id, outputs=[edit_text, edit_author, edit_tags, edit_message])
                update_btn.click(fn=update_quote, inputs=[edit_id, edit_text, edit_author, edit_tags], outputs=[edit_message, output])

            with gr.Accordion("🗑️ 명언 삭제", open=False):
                delete_id  = gr.Number(label="삭제할 명언 ID", precision=0)
                delete_btn = gr.Button("삭제")
                delete_message = gr.Markdown()
                delete_btn.click(fn=delete_quote, inputs=delete_id, outputs=[delete_message, output])


        with gr.Tab(" 저자 분석"):
            gr.Markdown("## 👤 저자 프로필")
            gr.Markdown("Wikipedia API에서 수집한 저자 메타데이터와 해당 저자의 명언 패턴을 확인합니다.")

            with gr.Row():
                author_dropdown = gr.Dropdown(
                    choices=get_author_choices(), label="저자 선택", filterable=True
                )
                author_btn = gr.Button("저자 정보 보기", variant="primary")

            with gr.Row():
                # 왼쪽: 사진
                with gr.Column(scale=1):
                    author_image = gr.Markdown()

                # 오른쪽: 기본 정보
                with gr.Column(scale=2):
                    author_info = gr.Markdown()

            with gr.Row():
                # 시그니처 단어
                with gr.Column():
                    author_signature = gr.Dataframe(
                        headers=["단어", "TF-IDF 점수"],
                        label="✨ 시그니처 단어"
                    )
                # 주요 태그
                with gr.Column():
                    author_tags = gr.Dataframe(
                        headers=["태그", "빈도"],
                        label="🏷️ 주요 태그"
                    )

            gr.Markdown("## 💬 이 저자의 명언")
            author_quotes = gr.Dataframe(
                headers=["ID", "명언", "단어 수", "태그"],
                label="저자 명언 목록",
                wrap=True
            )

            author_btn.click(
                fn=get_author_profile,
                inputs=author_dropdown,
                outputs=[author_image, author_info, author_signature, author_tags, author_quotes]
            )

        with gr.Tab(" 단어 · 태그 분석"):
            gr.Markdown("## 📊 기초 시각화 분석")
            gr.Markdown("명언 텍스트와 태그를 기준으로 단어 빈도, 워드클라우드, 길이 분포를 확인합니다.")

            with gr.Accordion("☁️ 전체 워드클라우드", open=True):
                wordcloud_btn  = gr.Button("워드클라우드 생성", variant="primary")
                wordcloud_plot = gr.Plot(label="워드클라우드")
                wordcloud_btn.click(fn=create_wordcloud_figure, inputs=[], outputs=wordcloud_plot)

            with gr.Accordion("📊 단어 빈도수", open=False):
                limit = gr.Slider(minimum=5, maximum=50, value=20, step=5, label="표시할 단어 개수")
                word_bar_btn  = gr.Button("단어 빈도 그래프 보기", variant="primary")
                word_bar_plot = gr.Plot(label="단어 빈도 막대그래프")
                word_bar_btn.click(fn=create_word_count_bar, inputs=limit, outputs=word_bar_plot)

            with gr.Accordion("📏 명언 길이 분포", open=False):
                with gr.Row():
                    length_btn       = gr.Button("긴 명언 Top 30 보기")
                    length_chart_btn = gr.Button("길이 분포 그래프 보기", variant="primary")

                length_output = gr.Dataframe(headers=["ID", "저자", "단어 수", "명언"], label="명언 길이", wrap=True)
                length_plot   = gr.Plot(label="명언 길이 히스토그램")

                length_btn.click(fn=get_length_distribution_table, inputs=[], outputs=length_output)
                length_chart_btn.click(fn=create_length_histogram, inputs=[], outputs=length_plot)

            with gr.Accordion("🏷️ 태그 빈도 분석", open=False):
                tag_limit     = gr.Slider(minimum=5, maximum=50, value=20, step=5, label="표시할 태그 개수")
                tag_chart_btn = gr.Button("태그 빈도 그래프 보기", variant="primary")
                tag_plot      = gr.Plot(label="태그 빈도 막대그래프")
                tag_chart_btn.click(fn=create_tag_bar_chart, inputs=tag_limit, outputs=tag_plot)

        with gr.Tab(" 시대 · 직업 분석"):
            gr.Markdown("## 📈 다차원 분석")
            gr.Markdown("저자의 시대, 직업 그룹, 태그 관계를 기준으로 명언 데이터를 분석합니다.")

            with gr.Accordion("1️⃣ 시대/직업별 명언 수", open=True):
                dimension_dropdown = gr.Dropdown(
                    choices=["occupation_group", "century"],
                    value="occupation_group", label="분석 기준"
                )
                dimension_btn  = gr.Button("차원별 명언 수 그래프", variant="primary")
                dimension_plot = gr.Plot(label="차원별 명언 수")
                dimension_btn.click(fn=create_dimension_bar_chart, inputs=dimension_dropdown, outputs=dimension_plot)

            with gr.Accordion("2️⃣ 직업 그룹별 시그니처 단어", open=False):
                occupation_dropdown = gr.Dropdown(choices=get_all_occupation_groups(), label="직업 그룹 선택")
                occupation_limit    = gr.Slider(minimum=5, maximum=30, value=10, step=5, label="시그니처 단어 개수")
                occupation_btn      = gr.Button("시그니처 단어 분석", variant="primary")
                occupation_output   = gr.Dataframe(headers=["단어", "TF-IDF 점수"], label="직업 그룹별 시그니처 단어")

                def occupation_signature_ui(group, limit):
                    if not group:
                        return []
                    words = get_occupation_group_signature_words(group, top_n=int(limit))
                    return [[w, round(s, 4)] for w, s in words]

                occupation_btn.click(
                    fn=occupation_signature_ui,
                    inputs=[occupation_dropdown, occupation_limit],
                    outputs=occupation_output
                )


            with gr.Accordion("4️⃣ 태그 동시출현 네트워크", open=False):
                network_limit = gr.Slider(minimum=10, maximum=50, value=30, step=5, label="표시할 태그 연결 수")
                network_btn   = gr.Button("태그 네트워크 생성", variant="primary")
                network_plot  = gr.Plot(label="태그 동시출현 네트워크")
                network_btn.click(fn=create_tag_network_figure, inputs=network_limit, outputs=network_plot)

        with gr.Tab(" 취향 분석 · 추천"):
            gr.Markdown("## 🎯 내 취향 기반 추천")
            gr.Markdown("즐겨찾기한 명언을 기반으로 취향을 분석하고, 규칙 기반/임베딩 기반 추천을 제공합니다.")

            with gr.Accordion("⭐ 즐겨찾기 관리", open=True):
                gr.Markdown("명언 탐색 탭에서 확인한 ID를 입력해 즐겨찾기에 추가하거나 해제할 수 있습니다.")

                with gr.Row():
                    fav_id         = gr.Number(label="명언 ID", precision=0)
                    add_fav_btn    = gr.Button("즐겨찾기 추가", variant="primary")
                    remove_fav_btn = gr.Button("즐겨찾기 해제")

                fav_message     = gr.Markdown()
                favorites_output = gr.Dataframe(headers=["ID", "명언", "저자", "태그"], label="내 즐겨찾기", wrap=True)
                refresh_fav_btn = gr.Button("즐겨찾기 목록 새로고침")

                add_fav_btn.click(fn=add_favorite_ui, inputs=fav_id, outputs=[fav_message, favorites_output])
                remove_fav_btn.click(fn=remove_favorite_ui, inputs=fav_id, outputs=[fav_message, favorites_output])
                refresh_fav_btn.click(fn=get_favorites_table, inputs=[], outputs=favorites_output)
                demo.load(fn=get_favorites_table, inputs=[], outputs=favorites_output)

            with gr.Accordion("📊 내 취향 분석", open=False):
                profile_btn    = gr.Button("내 취향 분석하기", variant="primary")
                profile_output = gr.Markdown()
                profile_btn.click(fn=get_favorite_profile_text, inputs=[], outputs=profile_output)

            with gr.Accordion("🎁 규칙 기반 추천", open=False):
                gr.Markdown("즐겨찾기한 명언의 저자, 태그, 단어 패턴을 기반으로 추천합니다.")
                recommend_limit  = gr.Slider(minimum=3, maximum=15, value=5, step=1, label="추천 개수")
                recommend_btn    = gr.Button("추천 받기", variant="primary")
                recommend_output = gr.Dataframe(
                    headers=["ID", "명언", "저자", "태그", "매칭 점수", "추천 이유"],
                    label="추천 결과", wrap=True
                )
                recommend_btn.click(fn=recommend_quotes_ui, inputs=recommend_limit, outputs=recommend_output)

            with gr.Accordion("🧠 의미 기반 추천", open=False):
                gr.Markdown("즐겨찾기한 명언들의 임베딩 평균을 이용해 의미적으로 가까운 명언을 추천합니다.")
                embedding_limit  = gr.Slider(minimum=3, maximum=15, value=5, step=1, label="의미 기반 추천 개수")
                embedding_btn    = gr.Button("의미 기반 추천 받기", variant="primary")
                embedding_output = gr.Dataframe(
                    headers=["ID", "명언", "저자", "태그", "매칭 점수", "추천 이유"],
                    label="의미 기반 추천 결과", wrap=True
                )
                embedding_btn.click(fn=embedding_recommend_ui, inputs=embedding_limit, outputs=embedding_output)

    return demo