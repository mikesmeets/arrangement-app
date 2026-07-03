from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

# Keyword -> hex color. Matched by substring against Flower.color (case-insensitive),
# so compound names like "Antique Pink" or "Silver-Green" still resolve sensibly.
COLOR_KEYWORDS = [
    ("champagne", "#e8cfa0"),
    ("cream", "#f5eddb"),
    ("ivory", "#f7f2e7"),
    ("lavender", "#b9a4d4"),
    ("purple", "#8e5fc2"),
    ("silver", "#c9c9c9"),
    ("white", "#fafafa"),
    ("yellow", "#f2c94c"),
    ("orange", "#e0792c"),
    ("peach", "#f2b48c"),
    ("pink", "#e874a1"),
    ("red", "#c62839"),
    ("burgundy", "#6e1f2a"),
    ("blue", "#3a7bd5"),
    ("green", "#4a9c5d"),
    ("brown", "#7b5030"),
    ("black", "#2b2226"),
]

BLOOM_OUTLINE = "#2b2226"
STEM_GREEN = "#4a9c5d"
BG = "#faf7f8"


def colors_for(color_name):
    """Return one or two hex colors to render for this flower's color name."""
    name = color_name.lower()
    matches = [hex_code for keyword, hex_code in COLOR_KEYWORDS if keyword in name]
    if matches:
        return matches[:2]
    # Unrecognized / compound names like "Bi-Color" get a two-tone split.
    return ["#e874a1", "#f2c94c"]


def render_thumbnail(flower):
    size = 200
    img = Image.new("RGB", (size, size), BG)
    draw = ImageDraw.Draw(img)
    bloom_box = [40, 25, 160, 145]

    colors = colors_for(flower.color)
    if len(colors) == 1:
        draw.ellipse(bloom_box, fill=colors[0], outline=BLOOM_OUTLINE, width=3)
    else:
        draw.pieslice(bloom_box, start=90, end=270, fill=colors[0], outline=BLOOM_OUTLINE, width=3)
        draw.pieslice(bloom_box, start=270, end=90, fill=colors[1], outline=BLOOM_OUTLINE, width=3)

    # Stem + leaf, so it reads as a flower rather than a plain circle.
    draw.line([100, 145, 100, 180], fill=STEM_GREEN, width=6)
    draw.ellipse([82, 155, 112, 172], fill=STEM_GREEN)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"flower_{flower.pk}.png")
