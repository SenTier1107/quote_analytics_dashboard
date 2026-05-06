from collections import Counter
import re
import platform

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.colors as mcolors
from wordcloud import WordCloud

from core.database import get_connection


def set_korean_font():
    system = platform.system()
    if system == "Windows":
        plt.rcParams["font.family"] = "Malgun Gothic"
    else:
        try:
            fm.fontManager.addfont("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
            plt.rcParams["font.family"] = "NanumGothic"
        except Exception:
            plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False

set_korean_font()


STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "to", "of", "in", "on", "for", "with", "as", "by", "at", "from",
    "it", "this", "that", "you", "your", "i", "me", "my", "we", "our",
    "they", "them", "their", "he", "she", "his", "her", "be", "been",
    "have", "has", "had", "do", "does", "did", "not", "no", "so",
    "if", "then", "than", "too", "very", "can", "will", "just"
}

ORANGE_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "orange_grad", ["#ffcc80", "#ffa726", "#f57c00", "#e65c00"]
)


def orange_colors(n):
    return [ORANGE_CMAP(i / max(n - 1, 1)) for i in range(n)]


def tokenize(text: str):
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return [word for word in words if word not in STOPWORDS and len(word) >= 3]


def get_word_counter():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT text FROM quotes")
    rows = cur.fetchall()
    conn.close()
    counter = Counter()
    for row in rows:
        counter.update(tokenize(row["text"]))
    return counter


def create_wordcloud_figure():
    counter = get_word_counter()
    fig, ax = plt.subplots(figsize=(10, 5))

    if not counter:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        ax.axis("off")
        plt.close(fig)
        return fig

    wordcloud = WordCloud(
        width=1000,
        height=500,
        background_color="white",
        colormap="YlOrRd"
    ).generate_from_frequencies(counter)

    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")
    ax.set_title("전체 워드클라우드", fontsize=14, fontweight="bold", pad=12)

    plt.close(fig)
    return fig


def create_word_count_bar(top_n=20):
    counter = get_word_counter()
    common_words = counter.most_common(int(top_n))

    # 단어 수에 비례해서 그래프 너비 동적 조절
    fig_width = max(10, int(top_n) * 0.6)
    fig, ax = plt.subplots(figsize=(fig_width, 5))

    if not common_words:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        plt.close(fig)
        return fig

    words  = [item[0] for item in common_words]
    counts = [item[1] for item in common_words]
    colors = orange_colors(len(words))

    bars = ax.bar(words, counts, color=colors, edgecolor="white", linewidth=0.5)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(count),
            ha="center", va="bottom", fontsize=8
        )

    ax.set_title(f"상위 {int(top_n)}개 단어 빈도", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("단어")
    ax.set_ylabel("빈도수")
    font_size = max(6, 12 - int(top_n) // 10)
    ax.tick_params(axis="x", rotation=45, labelsize=font_size)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    plt.close(fig)
    return fig


def create_length_histogram():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT word_count FROM quotes WHERE word_count IS NOT NULL")
    rows = cur.fetchall()
    conn.close()

    word_counts = [row["word_count"] for row in rows]
    fig, ax = plt.subplots(figsize=(10, 5))

    if not word_counts:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        plt.close(fig)
        return fig

    ax.hist(word_counts, bins=15, color="#f57c00", edgecolor="white", linewidth=0.5, alpha=0.9)
    ax.set_title("명언 길이 분포", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("단어 수")
    ax.set_ylabel("명언 수")
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    plt.close(fig)
    return fig


def create_tag_bar_chart(top_n=20):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT tag, COUNT(*) AS count
    FROM quote_tags
    GROUP BY tag ORDER BY count DESC LIMIT ?
    """, (int(top_n),))
    rows = cur.fetchall()
    conn.close()

    tags   = [row["tag"]   for row in rows]
    counts = [row["count"] for row in rows]

    # 태그 수에 비례해서 그래프 너비 동적 조절
    fig_width = max(10, int(top_n) * 0.6)
    fig, ax = plt.subplots(figsize=(fig_width, 5))

    if not tags:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        plt.close(fig)
        return fig

    colors = orange_colors(len(tags))
    bars = ax.bar(tags, counts, color=colors, edgecolor="white", linewidth=0.5)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(count),
            ha="center", va="bottom", fontsize=8
        )

    ax.set_title(f"상위 {int(top_n)}개 태그 빈도", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("태그")
    ax.set_ylabel("빈도수")
    font_size = max(6, 12 - int(top_n) // 10)
    ax.tick_params(axis="x", rotation=45, labelsize=font_size)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    plt.close(fig)
    return fig


def create_dimension_bar_chart(dimension="occupation_group"):
    conn = get_connection()
    cur = conn.cursor()

    if dimension == "century":
        cur.execute("""
        SELECT COALESCE(a.century, '정보 없음') AS label, COUNT(q.id) AS count
        FROM quotes q LEFT JOIN authors a ON q.author = a.name
        GROUP BY label ORDER BY count DESC
        """)
    else:
        cur.execute("""
        SELECT COALESCE(a.occupation_group, 'Other') AS label, COUNT(q.id) AS count
        FROM quotes q LEFT JOIN authors a ON q.author = a.name
        GROUP BY label ORDER BY count DESC
        """)

    rows = cur.fetchall()
    conn.close()

    labels = [row["label"] for row in rows]
    counts = [row["count"] for row in rows]
    fig, ax = plt.subplots(figsize=(10, 5))

    if not labels:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        plt.close(fig)
        return fig

    colors = orange_colors(len(labels))
    bars = ax.bar(labels, counts, color=colors, edgecolor="white", linewidth=0.5)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(count),
            ha="center", va="bottom", fontsize=9
        )

    label_kr = "시대별" if dimension == "century" else "직업별"
    ax.set_title(f"{label_kr} 명언 수", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel(label_kr)
    ax.set_ylabel("명언 수")
    ax.tick_params(axis="x", rotation=45)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    plt.close(fig)
    return fig


def create_occupation_tag_heatmap(top_tags=10):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT tag, COUNT(*) AS count
    FROM quote_tags GROUP BY tag ORDER BY count DESC LIMIT ?
    """, (int(top_tags),))
    tags = [row["tag"] for row in cur.fetchall()]

    cur.execute("""
    SELECT DISTINCT COALESCE(occupation_group, 'Other') AS group_name
    FROM authors ORDER BY group_name
    """)
    groups = [row["group_name"] for row in cur.fetchall()]

    matrix = []
    for group in groups:
        row_values = []
        for tag in tags:
            cur.execute("""
            SELECT COUNT(*) AS count
            FROM quotes q
            JOIN authors a ON q.author = a.name
            JOIN quote_tags qt ON q.id = qt.quote_id
            WHERE COALESCE(a.occupation_group, 'Other') = ? AND qt.tag = ?
            """, (group, tag))
            row_values.append(cur.fetchone()["count"])
        matrix.append(row_values)

    conn.close()

    fig, ax = plt.subplots(figsize=(12, 6))

    if not tags or not groups:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        plt.close(fig)
        return fig

    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd")

    ax.set_xticks(range(len(tags)))
    ax.set_xticklabels(tags, rotation=45, ha="right")
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels(groups)

    max_val = max(max(r) for r in matrix) if matrix else 1
    for i in range(len(groups)):
        for j in range(len(tags)):
            ax.text(j, i, str(matrix[i][j]),
                    ha="center", va="center", fontsize=8,
                    color="white" if matrix[i][j] > max_val * 0.5 else "black")

    ax.set_title("직업 그룹 × 태그 히트맵", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("태그")
    ax.set_ylabel("직업 그룹")
    fig.colorbar(im, ax=ax, label="명언 수")

    fig.tight_layout()
    plt.close(fig)
    return fig