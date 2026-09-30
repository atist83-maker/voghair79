"""VOG HAIR 아뜰리에점 컬러 스타일 릴스 생성 (1080x1920, 30fps)

작은 정사각형 스타일 사진용 레이아웃: 같은 사진을 흐리게 깐 배경 위에
사진 카드를 올리고 천천히 줌 + 크로스페이드 + 한글 자막, 마지막에 매장 안내 화면.
사용: python3 reels/make_atelier_reel.py <사진 폴더> <출력.mp4> [폰트 폴더]
폰트 폴더에는 Pretendard-Bold.otf / Pretendard-SemiBold.otf / Pretendard-Regular.otf 가 있어야 함.
"""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
SHOT = 3.4   # 사진 1장 노출 시간(초)
FADE = 0.5   # 크로스페이드(초)
END = 3.8    # 엔딩 카드(초)
CARD = 880   # 사진 카드 한 변(px)
CARD_Y = 330  # 사진 카드 위쪽 위치

# (파일, 큰 자막, 작은 자막, 줌 방향)
SHOTS = [
    ("1.jpg", "머리색만 바꿨을 뿐인데", "밀크브라운 롱웨이브", "in"),
    ("2.jpg", "분위기가 완전히 달라져요", "파스텔 핑크 레이어드", "out"),
    ("3.jpg", "내 톤에 맞춘 컬러로", "로즈 핑크 단발", "in"),
    ("4.jpg", "포인트까지 섬세하게", "블루 투톤 웨이브", "out"),
]
STORE = "보그헤어 아뜰리에점"
HANDLE = "@voghair_k"
CTA = "네이버 예약으로 만나요"

INK, SUB, ACCENT, CREAM = (45, 40, 36), (110, 100, 92), (214, 120, 140), (248, 242, 238)
FONTS = {}


def font(weight, size):
    return ImageFont.truetype(str(FONTS[weight]), size)


def warm(img):
    r, g, b = img.split()
    return Image.merge("RGB", (r.point(lambda v: min(255, int(v * 1.03 + 3))), g, b.point(lambda v: int(v * 0.97))))


def prepare(img):
    """(흐린 배경, 사진 카드 원본) 반환. 카드는 줌 여백을 위해 10% 크게 만들어 둔다."""
    img = warm(img)
    bg = img.resize((H, H), Image.LANCZOS).crop(((H - W) // 2, 0, (H + W) // 2, H))
    bg = bg.filter(ImageFilter.GaussianBlur(40))
    bg = ImageEnhance.Brightness(bg).enhance(0.72)
    side = min(img.size)
    sq = img.crop(((img.width - side) // 2, (img.height - side) // 2,
                   (img.width + side) // 2, (img.height + side) // 2))
    big = sq.resize((int(CARD * 1.1),) * 2, Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    return bg, big


MASK = Image.new("L", (CARD, CARD), 0)
ImageDraw.Draw(MASK).rounded_rectangle([(0, 0), (CARD - 1, CARD - 1)], radius=44, fill=255)
SHADOW = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(SHADOW).rounded_rectangle(
    [((W - CARD) // 2, CARD_Y + 18), ((W + CARD) // 2, CARD_Y + CARD + 18)], radius=44, fill=(0, 0, 0, 110))
SHADOW = SHADOW.filter(ImageFilter.GaussianBlur(24))


def compose(bg, big, t, direction):
    """t: 0..1. 카드 안 사진이 1.0 -> 1.08 (in) 또는 반대(out) 로 줌."""
    z = 1.0 + 0.08 * (t if direction == "in" else 1 - t)
    c = big.width / 1.1 / z
    o = (big.width - c) / 2
    card = big.resize((CARD, CARD), Image.BILINEAR, box=(o, o, o + c, o + c))
    frame = bg.convert("RGBA")
    frame.alpha_composite(SHADOW)
    frame.paste(card, ((W - CARD) // 2, CARD_Y), MASK)
    return frame


def header_layer():
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((W // 2, 200), "VOG HAIR ATELIER", font=font("SemiBold", 44), anchor="mm", fill=(255, 255, 255, 235))
    d.line([(W // 2 - 30, 250), (W // 2 + 30, 250)], fill=(255, 255, 255, 180), width=3)
    return layer


def text_layer(idx, big, small, alpha):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if alpha <= 0:
        return layer
    a = int(255 * alpha)
    d = ImageDraw.Draw(layer)
    # 카드 위 번호 라벨
    tag = f"COLOR {idx + 1:02d}"
    ft = font("SemiBold", 32)
    tw = d.textlength(tag, font=ft)
    x0, y0 = (W - CARD) // 2 + 36, CARD_Y + 36
    d.rounded_rectangle([(x0, y0), (x0 + tw + 44, y0 + 58)], radius=29, fill=(255, 255, 255, int(220 * alpha)))
    d.text((x0 + 22, y0 + 29), tag, font=ft, anchor="lm", fill=(*INK, a))
    # 하단 자막
    fb, fs = font("Bold", 70), font("Regular", 44)
    y_big = CARD_Y + CARD + 150
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((W // 2, y_big + 4), big, font=fb, anchor="mm", fill=(0, 0, 0, int(150 * alpha)))
    layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    d.text((W // 2, y_big), big, font=fb, anchor="mm", fill=(255, 255, 255, a))
    d.line([(W // 2 - 40, y_big + 72), (W // 2 + 40, y_big + 72)], fill=(*ACCENT, a), width=5)
    d.text((W // 2, y_big + 130), small, font=fs, anchor="mm", fill=(240, 236, 232, a))
    return layer


def end_card(thumbs):
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    # 스타일 썸네일 2x2
    s, gap = 300, 24
    x0 = (W - (2 * s + gap)) // 2
    y0 = 300
    m = Image.new("L", (s, s), 0)
    ImageDraw.Draw(m).rounded_rectangle([(0, 0), (s - 1, s - 1)], radius=28, fill=255)
    for i, t in enumerate(thumbs[:4]):
        img.paste(t.resize((s, s), Image.LANCZOS), (x0 + (i % 2) * (s + gap), y0 + (i // 2) * (s + gap)), m)
    y = y0 + 2 * s + gap + 130
    d.text((W // 2, y), "VOG HAIR ATELIER", font=font("Bold", 84), anchor="mm", fill=INK)
    d.text((W // 2, y + 95), STORE, font=font("Regular", 48), anchor="mm", fill=SUB)
    d.line([(W // 2 - 60, y + 170), (W // 2 + 60, y + 170)], fill=ACCENT, width=6)
    d.text((W // 2, y + 270), "나에게 맞는 컬러, 상담부터 편하게", font=font("SemiBold", 46), anchor="mm", fill=INK)
    d.rounded_rectangle([(190, y + 350), (W - 190, y + 470)], radius=60, fill=INK)
    d.text((W // 2, y + 410), HANDLE, font=font("Bold", 54), anchor="mm", fill=(255, 255, 255))
    d.text((W // 2, y + 540), CTA, font=font("Regular", 42), anchor="mm", fill=SUB)
    return img


def main(src_dir, out_path, font_dir):
    for w in ("Bold", "SemiBold", "Regular"):
        FONTS[w] = Path(font_dir) / f"Pretendard-{w}.otf"
    src = Path(src_dir)
    raws = [Image.open(src / f).convert("RGB") for f, *_ in SHOTS]
    prepared = [prepare(r) for r in raws]
    ending = end_card([warm(r) for r in raws])
    header = header_layer()

    n_shot, n_fade, n_end = int(SHOT * FPS), int(FADE * FPS), int(END * FPS)
    step = n_shot - n_fade
    total = step * len(SHOTS) + n_fade + n_end
    texts = {}

    def shot_frame(i, k):
        f, big, small, direction = SHOTS[i]
        frame = compose(*prepared[i], k / n_shot, direction)
        frame.alpha_composite(header)
        ta = min(1, max(0, (k - 6) / 10)) * min(1, max(0, (n_shot - n_fade - k) / 6 + 1))
        key = (i, round(ta, 2))
        if key not in texts:
            texts[key] = text_layer(i, big, small, ta)
        frame.alpha_composite(texts[key])
        return frame.convert("RGB")

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([
        ff, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-shortest", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", out_path,
    ], stdin=subprocess.PIPE)

    last_start = step * (len(SHOTS) - 1)
    for n in range(total):
        i = min(n // step, len(SHOTS) - 1)
        k = n - i * step
        if n >= last_start + n_shot - n_fade:
            # 마지막 컷 -> 엔딩 카드 크로스페이드
            kk = n - (last_start + n_shot - n_fade)
            frame = Image.blend(shot_frame(len(SHOTS) - 1, n - last_start), ending, kk / n_fade) if kk < n_fade else ending
        else:
            frame = shot_frame(i, k)
            if i > 0 and k < n_fade:
                frame = Image.blend(shot_frame(i - 1, k + step), frame, k / n_fade)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"done: {out_path} ({total / FPS:.1f}s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "reels/fonts")
