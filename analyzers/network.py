from itertools import combinations
from collections import Counter

from core.database import get_connection


def get_tag_cooccurrence_pairs(limit=30):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT quote_id, tag
    FROM quote_tags
    ORDER BY quote_id
    """)

    rows = cur.fetchall()
    conn.close()

    quote_tags = {}

    for row in rows:
        quote_id = row["quote_id"]
        tag = row["tag"]

        if quote_id not in quote_tags:
            quote_tags[quote_id] = []

        quote_tags[quote_id].append(tag)

    counter = Counter()

    for tags in quote_tags.values():
        unique_tags = sorted(set(tags))

        for tag1, tag2 in combinations(unique_tags, 2):
            counter[(tag1, tag2)] += 1

    return [
        {
            "tag1": tag1,
            "tag2": tag2,
            "count": count
        }
        for (tag1, tag2), count in counter.most_common(int(limit))
    ]