from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "shots"
FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"

ITEMS = [
    ("a-wechat.png", "A", "微信原生清爽", "白底 · 微信绿 · 弱阴影", "#07C160"),
    ("b-apple.png", "B", "Apple 浅色卡片", "柔和阴影 · 蓝色主调", "#4A90E2"),
    ("c-editorial.png", "C", "中文账本 / 编辑", "米白纸感 · 宋体 · 细线", "#B33A2B"),
    ("d-dark.png", "D", "深色数据", "深灰 · 荧光绿 · 数据感", "#5BE49B"),
    ("e-soft.png", "E", "柔和亲和", "奶油底 · 珊瑚色 · 大圆角", "#E86A5A"),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def main() -> None:
    phone_w, phone_h = 375, 812
    margin, gap, header_h, label_h = 40, 26, 112, 76
    width = margin * 2 + phone_w * len(ITEMS) + gap * (len(ITEMS) - 1)
    height = header_h + phone_h + label_h + 24
    canvas = Image.new("RGB", (width, height), "#F2F3F5")
    draw = ImageDraw.Draw(canvas)

    draw.text((margin, 24), "荣小账 · 5 套 UI 方向", font=font(40, True), fill="#1D1D1F")
    draw.text(
        (margin, 76),
        "同一份首页内容 · 375×812 · 仅用于选风格，不是最终小程序",
        font=font(20),
        fill="#6E6E73",
    )
    draw.text(
        (width - margin - 190, 34),
        "2026-10-28 · HTML 样稿",
        font=font(16),
        fill="#86868B",
    )

    for index, (filename, letter, title, subtitle, brand) in enumerate(ITEMS):
        x = margin + index * (phone_w + gap)
        y = header_h
        image = Image.open(SHOTS / filename).convert("RGB")
        if image.size != (phone_w, phone_h):
            image = image.resize((phone_w, phone_h), Image.LANCZOS)
        canvas.paste(image, (x, y))
        draw.rectangle((x - 1, y - 1, x + phone_w, y + phone_h), outline="#D5D9E0")

        cy = y + phone_h + 20
        draw.ellipse((x + 2, cy + 2, x + 16, cy + 16), fill=brand)
        draw.text((x + 24, cy - 4), f"{letter} · {title}", font=font(23, True), fill="#1D1D1F")
        draw.text((x + 24, cy + 30), subtitle, font=font(15), fill="#6E6E73")

    canvas.save(ROOT / "shots" / "compare-all.png")
    canvas.save(ROOT / "shots" / "compare-all.jpg", quality=92)
    print("saved compare-all", canvas.size)


if __name__ == "__main__":
    main()
