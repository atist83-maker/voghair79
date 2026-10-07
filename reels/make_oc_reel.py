"""OC 저손상 탈색 릴스 (1080x1920, 30fps)

결과 먼저(훅) -> 시술 전 -> 탈색 과정 -> 결과 -> 사진 -> 엔딩 카드.
사용: python3 reels/make_oc_reel.py <업로드 폴더> <출력.mp4>
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
FADE = 0.4
FF = imageio_ffmpeg.get_ffmpeg_exe()
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
KR = 1

# (소스 패턴, 시작초, 길이, 큰 자막, 작은 자막)
SEGMENTS = [
    ("*IMG_7175.mov", 0.0, 3.0, "탈색하면 머리 녹는다고요?", "이거 보세요"),
    ("*IMG_6417.mov", 0.0, 4.5, "자라난 뿌리, 올라온 노란기", "이런 고민 있으셨죠"),
    ("*IMG_6420.mov", 0.0, 4.7, "OC 저손상 탈색", "손상은 줄이고, 밝기는 올리고"),
    ("*IMG_7175.mov", 3.0, 4.4, "노란기 없이 맑은 톤", "머릿결까지 부드럽게"),
]
PHOTO = ("*image.jpg", 2.2, "탈색 후에도 이 결", "보그헤어아뜰리에 배곧점")
END = 3.6
OFFERS = [("네이버 예약 시", "20% 할인"), ("첫 방문 염색·열펌", "30~40% 할인")]


def font(path, size):
    return ImageFont.truetype(path, size, index=KR)


def caption_png(big, small, path):
    """화면 위쪽(인스타 UI를 피한 자리)에 올릴 자막 레이어."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        grad.putpixel((0, y), int(max(0.0, 1 - y / (H * 0.45)) * 140))
    img.putalpha(grad.resize((W, H)))
    fb, fs = font(FONT_BOLD, 70), font(FONT_REG, 42)
    y = int(H * 0.2)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((W // 2, y + 4), big, font=fb, anchor="mm", fill=(0, 0, 0, 170))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    d.text((W // 2, y), big, font=fb, anchor="mm", fill="white")
    d.line([(W // 2 - 40, y + 66), (W // 2 + 40, y + 66)], fill=(232, 120, 40), width=5)
    d.text((W // 2, y + 120), small, font=fs, anchor="mm", fill=(240, 240, 240))
    img.save(path)


def end_card(path):
    img = Image.new("RGB", (W, H), (244, 243, 240))
    d = ImageDraw.Draw(img)
    ink, sub, accent = (40, 40, 40), (105, 105, 105), (232, 120, 40)
    d.text((W // 2, 520), "VOG HAIR ATELIER", font=font(FONT_BOLD, 84), anchor="mm", fill=ink)
    d.text((W // 2, 610), "보그헤어아뜰리에 배곧점", font=font(FONT_REG, 46), anchor="mm", fill=sub)
    d.line([(W // 2 - 60, 690), (W // 2 + 60, 690)], fill=accent, width=6)
    y = 780
    for label, value in OFFERS:
        d.rounded_rectangle([(150, y), (W - 150, y + 190)], radius=28, fill="white")
        d.text((W // 2, y + 58), label, font=font(FONT_REG, 42), anchor="mm", fill=sub)
        d.text((W // 2, y + 128), value, font=font(FONT_BOLD, 64), anchor="mm", fill=accent)
        y += 230
    d.rounded_rectangle([(190, y + 30), (W - 190, y + 150)], radius=60, fill=ink)
    d.text((W // 2, y + 90), "댓글에 '예약' 남겨주세요", font=font(FONT_BOLD, 50), anchor="mm", fill="white")
    d.text((W // 2, y + 220), "@voghair_k · 시흥 배곧신도시", font=font(FONT_REG, 40), anchor="mm", fill=sub)
    img.save(path)


def run(args):
    subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)


def fit():
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1"


def main(src_dir, out):
    src, tmp = Path(src_dir), Path(tempfile.mkdtemp())
    parts, lens = [], []
    for i, (pat, ss, dur, big, small) in enumerate(SEGMENTS):
        cap = tmp / f"cap{i}.png"
        caption_png(big, small, cap)
        clip = tmp / f"seg{i}.mp4"
        run(["-ss", str(ss), "-t", str(dur), "-i", str(next(src.glob(pat))), "-loop", "1", "-i", str(cap),
             "-filter_complex",
             f"[0:v]{fit()}[v];[1:v]format=rgba,fade=in:st=0.25:d=0.3:alpha=1[c];"
             f"[v][c]overlay=0:0:shortest=1,format=yuv420p",
             "-an", "-t", str(dur), "-c:v", "libx264", "-crf", "16", "-preset", "medium", str(clip)])
        parts.append(clip)
        lens.append(dur)

    # 사진: 천천히 줌인 + 자막
    pat, dur, big, small = PHOTO
    cap = tmp / "cap_photo.png"
    caption_png(big, small, cap)
    n = int(dur * FPS)
    clip = tmp / "photo.mp4"
    run(["-loop", "1", "-i", str(next(src.glob(pat))), "-loop", "1", "-i", str(cap), "-filter_complex",
         f"[0:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
         f"zoompan=z='1+0.06*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS}[v];"
         f"[1:v]format=rgba,fade=in:st=0.2:d=0.3:alpha=1[c];[v][c]overlay=0:0:shortest=1,format=yuv420p",
         "-t", str(dur), "-c:v", "libx264", "-crf", "16", str(clip)])
    parts.append(clip)
    lens.append(dur)

    card = tmp / "end.png"
    end_card(card)
    clip = tmp / "end.mp4"
    run(["-loop", "1", "-i", str(card), "-vf", f"fps={FPS},format=yuv420p", "-t", str(END),
         "-c:v", "libx264", "-crf", "16", str(clip)])
    parts.append(clip)
    lens.append(END)

    # 크로스페이드로 이어붙이기 + 무음 오디오(음악은 인스타에서)
    inputs, chain, prev, t = [], [], "0:v", 0.0
    for p in parts:
        inputs += ["-i", str(p)]
    for i in range(1, len(parts)):
        t += lens[i - 1] - FADE
        label = f"x{i}"
        chain.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={FADE}:offset={t:.2f}[{label}]")
        prev = label
    total = sum(lens) - FADE * (len(parts) - 1)
    run([*inputs, "-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo",
         "-filter_complex", ";".join(chain), "-map", f"[{prev}]", "-map", f"{len(parts)}:a",
         "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out])
    print(f"done: {out} ({total:.1f}s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
