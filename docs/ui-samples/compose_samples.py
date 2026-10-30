from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def cover(path: Path, height: int) -> Image.Image:
    image = Image.open(path).convert("RGB")
    width = round(image.width * height / image.height)
    return image.resize((width, height), Image.LANCZOS)


def compose_app_styles() -> None:
    items = [
        ("huashu-app-birding.jpg", "A · 贴纸手账风", "轻松、亲切，适合养成记账习惯"),
        ("huashu-app-recipe.jpg", "B · 中文编辑风", "克制、有文化感，适合账本/内容"),
        ("huashu-app-plant.jpg", "C · 深色高级风", "专业、数据感，适合统计与夜间"),
    ]
    height = 900
    images = [cover(ROOT / name, height) for name, _, _ in items]
    margin, gap, header, caption = 48, 28, 110, 74
    width = margin * 2 + sum(image.width for image in images) + gap * (len(images) - 1)
    canvas = Image.new("RGB", (width, header + height + caption), "#F5F5F7")
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 30), "三种 App 风格方向（huashu-design 真实产出）", font=font(38, True), fill="#1D1D1F")
    draw.text((margin, 76), "同一款 App，换一套视觉语言，用户感受完全不同。", font=font(22), fill="#6E6E73")

    x = margin
    for image, (_, title, subtitle) in zip(images, items):
        canvas.paste(image, (x, header))
        draw.text((x, header + height + 12), title, font=font(26, True), fill="#1D1D1F")
        draw.text((x, header + height + 44), subtitle, font=font(20), fill="#6E6E73")
        x += image.width + gap
    canvas.save(ROOT / "app-style-samples.jpg", quality=92)
    print("saved app-style-samples.jpg", canvas.size)


def compose_impeccable() -> None:
    height = 860
    mockup = cover(ROOT / "impeccable-mockup.jpg", height)
    site = Image.open(ROOT / "impeccable-working-site.png").convert("RGB")
    site = site.crop((0, 0, site.width, min(1800, site.height)))
    site = site.resize((round(site.width * height / site.height), height), Image.LANCZOS)
    margin, gap, header, caption = 44, 26, 104, 64
    width = margin * 2 + mockup.width + gap + site.width
    canvas = Image.new("RGB", (width, header + height + caption), "#F5F5F7")
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 26), "组合 1 的工作方式：先设计稿，再落地", font=font(36, True), fill="#1D1D1F")
    draw.text((margin, 72), "Impeccable 会先定视觉方向，再把设计变成可用的页面并逐项检查。", font=font(21), fill="#6E6E73")
    canvas.paste(mockup, (margin, header))
    canvas.paste(site, (margin + mockup.width + gap, header))
    draw.text((margin, header + height + 10), "① 设计稿（mockup）", font=font(24, True), fill="#1D1D1F")
    draw.text((margin + mockup.width + gap, header + height + 10), "② 落地页（working site）", font=font(24, True), fill="#1D1D1F")
    canvas.save(ROOT / "impeccable-before-after.jpg", quality=92)
    print("saved impeccable-before-after.jpg", canvas.size)


if __name__ == "__main__":
    compose_app_styles()
    compose_impeccable()
