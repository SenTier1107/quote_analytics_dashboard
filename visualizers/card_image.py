from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont

from core.database import get_connection


BASE_DIR = Path(__file__).resolve().parent.parent
CARD_DIR = BASE_DIR / "assets" / "cards"
CARD_DIR.mkdir(parents=True, exist_ok=True)


def get_default_font(size=32):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except (IOError, OSError):  # 폰트 파일 없을 때만 처리
        return ImageFont.load_default()


def create_quote_card(quote_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT id, text, author
    FROM quotes
    WHERE id = ?
    """, (quote_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    width, height = 1000, 600
    image = Image.new("RGB", (width, height), color=(250, 250, 245))
    draw = ImageDraw.Draw(image)

    title_font = get_default_font(36)
    quote_font = get_default_font(32)
    author_font = get_default_font(26)
    footer_font = get_default_font(18)

    margin = 80

    draw.text(
        (margin, 50),
        "Quote Insight Dashboard",
        fill=(60, 60, 60),
        font=title_font
    )

    wrapped_quote = textwrap.fill(row["text"], width=42)

    draw.text(
        (margin, 160),
        f"\u201c{wrapped_quote}\u201d",
        fill=(30, 30, 30),
        font=quote_font,
        spacing=12
    )

    draw.text(
        (margin, 440),
        f"— {row['author']}",
        fill=(80, 80, 80),
        font=author_font
    )

    draw.text(
        (margin, 540),
        f"Quote ID: {row['id']}",
        fill=(120, 120, 120),
        font=footer_font
    )

    output_path = CARD_DIR / f"quote_{quote_id}.png"
    image.save(output_path)

    return str(output_path)