msg = "buatkan saya gambar cicak berkepala naga"
msg_lower = msg.lower()

IMAGE_GEN_PATTERNS = [
    "buatkan gambar", "bikin gambar", "buat foto", "buat ilustrasi", "generate image",
    "generate picture", "buat gambar", "bikin foto", "create image", "create picture",
    "gambarkan", "ilustrasikan", "buatkan foto", "bikin ilustrasi", "make image",
    "draw", "sketch", "render gambar", "lukiskan", "desainkan gambar",
]

matched = [p for p in IMAGE_GEN_PATTERNS if p in msg_lower]
print("Matches:", matched)
print("Is image?", bool(matched))
