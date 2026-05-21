import re

messages = [
    "buatkan saya gambar cicak berkepala naga",
    "bikin foto kucing yang lucu",
    "saya mau gambar pemandangan matahari terbenam",
    "tolong bikinkan gambar naga hitam",
    "bisa buatkan gambar robot?",
    "gambar anjing yang sedang tidur",
]

# Old pattern (substring match)
IMAGE_GEN_PATTERNS_OLD = [
    "buatkan gambar", "bikin gambar", "buat foto", "buat ilustrasi", "generate image",
    "generate picture", "buat gambar", "bikin foto", "create image", "create picture",
    "gambarkan", "ilustrasikan", "buatkan foto", "bikin ilustrasi", "make image",
    "draw", "sketch", "render gambar", "lukiskan", "desainkan gambar",
]

# New regex pattern
IMAGE_GEN_REGEX = re.compile(
    r'\b(buatkan|bikin|buat|tolong|coba|hasilkan|generate|create|make|draw)\b.{0,30}\b(gambar|foto|ilustrasi|image|picture|photo)\b'
    r'|'
    r'\b(gambar|foto|lukiskan|gambarkan|ilustrasikan)\b.{0,20}\b(\w+)\b',
    re.IGNORECASE
)

for msg in messages:
    old_match = any(p in msg.lower() for p in IMAGE_GEN_PATTERNS_OLD)
    new_match = bool(IMAGE_GEN_REGEX.search(msg.lower()))
    print(f"'{msg[:50]}': old={old_match}, new={new_match}")
