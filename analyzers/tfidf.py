from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer

from core.database import get_connection


STOPWORDS = [
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "to", "of", "in", "on", "for", "with", "as", "by", "at", "from",
    "it", "this", "that", "you", "your", "i", "me", "my", "we", "our",
    "they", "them", "their", "he", "she", "his", "her", "be", "been",
    "have", "has", "had", "do", "does", "did", "not", "no", "so",
    "if", "then", "than", "too", "very", "can", "will", "just",
    "one", "all", "what", "when", "where", "who", "why", "how",
    "there", "here", "into", "out", "up", "down", "over", "under"
]


def get_author_signature_words(author_name: str, top_n: int = 10):
    """
    특정 저자의 명언을 하나의 문서로 보고,
    다른 저자들과 비교했을 때 상대적으로 특징적인 단어를 TF-IDF로 추출한다.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT author, GROUP_CONCAT(text, ' ') AS document
    FROM quotes
    GROUP BY author
    HAVING document IS NOT NULL
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return []

    authors = [row["author"] for row in rows]
    documents = [row["document"] for row in rows]

    if author_name not in authors:
        return []

    # TF-IDF는 비교 대상이 2개 이상이어야 의미 있음
    if len(documents) < 2:
        return []

    vectorizer = TfidfVectorizer(
        stop_words=STOPWORDS,
        lowercase=True,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z']+\b",
        max_features=1000
    )

    matrix = vectorizer.fit_transform(documents)
    feature_names = vectorizer.get_feature_names_out()

    author_index = authors.index(author_name)
    scores = matrix[author_index].toarray()[0]

    word_scores = [
        (feature_names[i], float(scores[i]))
        for i in scores.argsort()[::-1]
        if scores[i] > 0
    ]

    return word_scores[:int(top_n)]


def get_occupation_group_signature_words(group_name: str, top_n: int = 10):
    """
    authors 테이블의 occupation_group을 기준으로 명언을 묶고,
    직업 그룹별 특징 단어를 TF-IDF로 추출한다.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT
        COALESCE(a.occupation_group, 'Other') AS occupation_group,
        q.text
    FROM quotes q
    LEFT JOIN authors a ON q.author = a.name
    """)

    rows = cur.fetchall()
    conn.close()

    group_docs = defaultdict(list)

    for row in rows:
        group_docs[row["occupation_group"]].append(row["text"])

    if group_name not in group_docs:
        return []

    groups = list(group_docs.keys())
    documents = [" ".join(group_docs[group]) for group in groups]

    # TF-IDF는 비교 대상이 2개 이상이어야 의미 있음
    if len(documents) < 2:
        return []

    vectorizer = TfidfVectorizer(
        stop_words=STOPWORDS,
        lowercase=True,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z']+\b",
        max_features=1000
    )

    matrix = vectorizer.fit_transform(documents)
    feature_names = vectorizer.get_feature_names_out()

    group_index = groups.index(group_name)
    scores = matrix[group_index].toarray()[0]

    word_scores = [
        (feature_names[i], float(scores[i]))
        for i in scores.argsort()[::-1]
        if scores[i] > 0
    ]

    return word_scores[:int(top_n)]


def get_all_occupation_groups():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT DISTINCT COALESCE(occupation_group, 'Other') AS occupation_group
    FROM authors
    ORDER BY occupation_group
    """)

    groups = [row["occupation_group"] for row in cur.fetchall()]
    conn.close()

    return groups