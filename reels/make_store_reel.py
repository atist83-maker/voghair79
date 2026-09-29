"""VOG HAIR 매장 소개 릴스 생성 (1080x1920, 30fps)

사진마다 천천히 줌(켄번스) + 크로스페이드 + 한글 자막, 마지막에 계정 안내 화면.
사용: python3 reels/make_store_reel.py <사진 폴더> <출력.mp4>
"""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
SHOT = 3.0   # 사진 1장 노출 시간(초)
FADE = 0.5   # 크로스페이드(초)
END = 3.8    # 엔딩 카드(초)

FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
KR = 1  # ttc 안의 KR 폰트 인덱스

# (파일, 큰 자막, 작은 자막, 줌 방향)
SHOTS = [
    ("2.jpg", "배곧에 이런 헤어샵이?", "보그헤어아뜰리에 배곧점", "in"),
    ("4.jpg", "AI로 진단하고", "내 두피·모발 상태부터 정확하게", "out"),
    ("3.jpg", "자연으로 치유합니다", "진단에 맞춘 케어", "in"),
    ("5.jpg", "OC 탈색, 저손상으로", "탈색 · 염색 시술", "out"),
    ("1.jpg", "고급스럽고 따뜻하게", "머무는 시간까지 편안한 공간", "in"),
]
HANDLE = "@voghair_k"
OFFERS = [("네이버 예약 시", "20% 할인"), ("첫 방문 염색·열펌", "30~40% 할인")]


def font(path, size):
    return ImageFont.truetype(path, size, index=KR)


def cover(img):
    """9:16 화면을 꽉 채우도록 약간 여유 있게(줌 여백) 리사이즈."""
    scale = max(W / img.width, H / img.height) * 1.12
    r, g, b = img.split()  # 살짝 따뜻한 톤
    img = Image.merge("RGB", (r.point(lambda v: min(255, int(v * 1.05 + 4))), g, b.point(lambda v: int(v * 0.93))))
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)


def kenburns(base, t, direction):
    """t: 0..1. 줌 1.0 -> 1.08 (in) 또는 반대(out) 로 가운데 크롭."""
    z = 1.0 + 0.08 * (t if direction == "in" else 1 - t)
    cw, ch = W * 1.1 / z, H * 1.1 / z
    left = (base.width - cw) / 2
    top = (base.height - ch) / 2
    return base.resize((W, H), Image.BILINEAR, box=(left, top, left + cw, top + ch))


def text_layer(big, small, alpha):
    """하단 자막 레이어 (RGBA). alpha: 0..1 페이드."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if alpha <= 0:
        return layer
    # 하단 그라데이션으로 가독성 확보
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        grad.putpixel((0, y), int(max(0, (y - H * 0.55) / (H * 0.45)) * 150))
    layer.putalpha(grad.resize((W, H)))
    d = ImageDraw.Draw(layer)
    fb, fs = font(FONT_BOLD, 72), font(FONT_REG, 42)
    a = int(255 * alpha)
    y_big = int(H * 0.74)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.text((W // 2, y_big + 4), big, font=fb, anchor="mm", fill=(0, 0, 0, int(160 * alpha)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    layer.alpha_composite(shadow)
    d.text((W // 2, y_big), big, font=fb, anchor="mm", fill=(255, 255, 255, a))
    d.line([(W // 2 - 40, y_big + 70), (W // 2 + 40, y_big + 70)], fill=(232, 120, 40, a), width=5)
    d.text((W // 2, y_big + 125), small, font=fs, anchor="mm", fill=(235, 235, 235, a))
    return layer


def end_card():
    img = Image.new("RGB", (W, H), (246, 241, 234))
    d = ImageDraw.Draw(img)
    ink, sub, accent = (45, 40, 36), (110, 100, 92), (232, 120, 40)
    d.text((W // 2, 560), "VOG HAIR ATELIER", font=font(FONT_BOLD, 84), anchor="mm", fill=ink)
    d.text((W // 2, 650), "보그헤어아뜰리에 배곧점", font=font(FONT_REG, 46), anchor="mm", fill=sub)
    d.text((W // 2, 715), "시흥 배곧신도시", font=font(FONT_REG, 38), anchor="mm", fill=sub)
    d.line([(W // 2 - 60, 790), (W // 2 + 60, 790)], fill=accent, width=6)
    y = 900
    for label, value in OFFERS:
        d.rounded_rectangle([(150, y), (W - 150, y + 190)], radius=28, fill=(255, 255, 255))
        d.text((W // 2, y + 58), label, font=font(FONT_REG, 42), anchor="mm", fill=sub)
        d.text((W // 2, y + 128), value, font=font(FONT_BOLD, 64), anchor="mm", fill=accent)
        y += 230
    d.text((W // 2, y + 90), HANDLE, font=font(FONT_BOLD, 52), anchor="mm", fill=ink)
    d.text((W // 2, y + 160), "네이버 예약으로 만나요", font=font(FONT_REG, 40), anchor="mm", fill=sub)
    return img


def main(src_dir, out_path):
    src = Path(src_dir)
    bases = [cover(Image.open(src / f).convert("RGB")) for f, *_ in SHOTS]
    ending = end_card()

    n_shot, n_fade, n_end = int(SHOT * FPS), int(FADE * FPS), int(END * FPS)
    step = n_shot - n_fade  # 다음 컷 시작 간격
    total = step * len(SHOTS) + n_fade + n_end

    def shot_frame(i, k):
        f, big, small, direction = SHOTS[i]
        frame = kenburns(bases[i], k / n_shot, direction).convert("RGBA")
        # 자막: 컷 시작 0.3초 뒤 페이드인, 끝나기 전 페이드아웃
        ta = min(1, max(0, (k - 9) / 10)) * min(1, max(0, (n_shot - n_fade - k) / 6 + 1))
        frame.alpha_composite(text_layer(big, small, ta))
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

    for n in range(total):
        i = min(n // step, len(SHOTS) - 1)
        k = n - i * step
        frame = shot_frame(i, k) if k < n_shot else ending
        # 크로스페이드: 이전 컷의 꼬리와 겹치기
        if i > 0 and k < n_fade:
            prev = shot_frame(i - 1, k + step)
            frame = Image.blend(prev, frame, k / n_fade)
        # 마지막 컷 -> 엔딩 카드 크로스페이드
        last_start = step * (len(SHOTS) - 1)
        if n >= last_start + n_shot - n_fade:
            kk = n - (last_start + n_shot - n_fade)
            if kk < n_fade:
                frame = Image.blend(shot_frame(len(SHOTS) - 1, n - last_start), ending, kk / n_fade)
            else:
                frame = ending
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"done: {out_path} ({total / FPS:.1f}s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
