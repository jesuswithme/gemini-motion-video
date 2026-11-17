"""plan.json + images/ + audio/ → 모션그래픽 MP4 + SRT
사용:
  python make_video.py <project_dir> preview 2.5 9 15   # 해당 초의 프레임을 frames/에 JPG로 저장
  python make_video.py <project_dir>                    # 전체 렌더 + 오디오 합성 → output/
필요: ffmpeg, pip install pillow numpy
"""
import json, math, os, random, subprocess, sys, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
BIG = (2304, 1296)
XF = 0.6                      # 장면 크로스페이드(초)
NAR_LEAD = [0.9, 0.5]         # 첫 장면 / 나머지 장면에서 나레이션 시작 지연
TAIL = 0.7                    # 나레이션 끝난 뒤 다음 장면까지 여유
END_HOLD = 2.0                # 마지막 장면 여유

P = sys.argv[1]
plan = json.load(open(f"{P}/plan.json", encoding="utf-8"))
SC = plan["scenes"]
N = len(SC)
ACC = tuple(plan.get("accent", [240, 120, 40]))

# ---------- 글꼴 (Windows / macOS / Linux) ----------
FONT_CANDIDATES = {
    "bold": ["C:/Windows/Fonts/malgunbd.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc",
             "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
             "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"],
    "regular": ["C:/Windows/Fonts/malgun.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"],
}


def kr_font(kind, size):
    for path in [plan.get(f"font_{kind}")] + FONT_CANDIDATES[kind]:
        if not path or not os.path.exists(path):
            continue
        if path.endswith(".ttc"):
            for idx in range(12):
                try:
                    f = ImageFont.truetype(path, size, index=idx)
                except Exception:
                    break
                if "KR" in " ".join(f.getname()) or "Gothic Neo" in " ".join(f.getname()):
                    return f
        return ImageFont.truetype(path, size)
    sys.exit("한글 글꼴을 찾지 못했습니다. plan.json에 font_bold / font_regular 경로를 넣어 주세요.")


F_HUGE, F_TITLE = kr_font("bold", 150), kr_font("bold", 112)
F_SUB, F_CAP, F_END = kr_font("regular", 44), kr_font("regular", 50), kr_font("regular", 40)


# ---------- 소재 ----------
def find(base, exts):
    return next((base + e for e in exts if os.path.exists(base + e)), None)


def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]))


def load_img(i):
    f = find(f"{P}/images/scene{i}", (".png", ".jpg", ".jpeg", ".webp"))
    if not f:
        sys.exit(f"images/scene{i} 이미지가 없습니다. generate.py를 먼저 실행하세요.")
    im = Image.open(f).convert("RGB")
    s = max(BIG[0] / im.width, BIG[1] / im.height)
    im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
    l, t = (im.width - BIG[0]) // 2, (im.height - BIG[1]) // 2
    return im.crop((l, t, l + BIG[0], t + BIG[1]))


NAR = [find(f"{P}/audio/n{i}", (".wav", ".mp3", ".m4a")) for i in range(1, N + 1)]
NDUR = [dur(f) if f else 0.0 for f in NAR]
LEAD = [NAR_LEAD[0] if i == 0 else NAR_LEAD[1] for i in range(N)]
SDUR = []
for i in range(N):
    base = LEAD[i] + NDUR[i] + (END_HOLD if i == N - 1 else TAIL)
    SDUR.append(max(base, SC[i].get("min_seconds", 4.5)))
starts, acc = [], 0.0
for i in range(N):
    starts.append(acc)
    acc += SDUR[i] - (XF if i < N - 1 else 0)
TOTAL = acc
CAPS = [(starts[i] + LEAD[i], starts[i] + LEAD[i] + NDUR[i] + 0.4, SC[i].get("caption") or SC[i].get("narration", ""))
        for i in range(N) if NDUR[i] > 0]

CAMS = {"in": ((1.00, .5, .5), (1.12, .5, .47)), "out": ((1.14, .5, .45), (1.00, .5, .5)),
        "left": ((1.10, .60, .5), (1.10, .40, .5)), "right": ((1.10, .40, .5), (1.10, .60, .5)),
        "up": ((1.10, .5, .62), (1.10, .5, .40)), "down": ((1.10, .5, .40), (1.10, .5, .60))}
DEFAULT_CAMS = ["in", "out", "in", "left", "out", "right", "in", "up"]


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def camera(img, i, u):
    (s0, x0, y0), (s1, x1, y1) = CAMS[SC[i].get("camera") or DEFAULT_CAMS[i % len(DEFAULT_CAMS)]]
    e = u * u * (3 - 2 * u)
    s = s0 + (s1 - s0) * e; cx = x0 + (x1 - x0) * e; cy = y0 + (y1 - y0) * e
    cw, ch = BIG[0] / s / 1.2, BIG[1] / s / 1.2
    l = min(max(cx * BIG[0] - cw / 2, 0), BIG[0] - cw); t = min(max(cy * BIG[1] - ch / 2, 0), BIG[1] - ch)
    return img.resize((W, H), Image.BILINEAR, box=(l, t, l + cw, t + ch))


# ---------- 입자 (단풍잎 / 꽃잎 / 눈) ----------
PTYPE = plan.get("particles", "maple")
PCOLS = {"maple": [(214, 48, 30), (235, 110, 25), (245, 170, 35), (190, 35, 35)],
         "petal": [(255, 200, 215), (250, 180, 200), (255, 225, 235)],
         "snow": [(255, 255, 255), (235, 242, 255)]}.get(PTYPE, [])
rng = random.Random(3)
PARTS = [dict(x=rng.uniform(0, W), y0=rng.uniform(-H, H), sp=rng.uniform(60, 150), r=rng.uniform(8, 26),
              sway=rng.uniform(30, 90), ph=rng.uniform(0, 6.28), rot=rng.uniform(-2, 2), col=rng.choice(PCOLS or [(0, 0, 0)]))
         for _ in range({"maple": 24, "petal": 30, "snow": 70}.get(PTYPE, 0))]
SHAPES = {}


def shape(r):
    key = round(r)
    if key not in SHAPES:
        pts = []
        for d in range(0, 360, 8):
            a = math.radians(d)
            k = (0.55 + 0.45 * abs(math.cos(2.5 * a)) ** 0.6) if PTYPE == "maple" else (0.6 + 0.4 * abs(math.cos(a))) if PTYPE == "petal" else 1
            pts.append((math.sin(a) * key * k, -math.cos(a) * key * k))
        SHAPES[key] = pts
    return SHAPES[key]


def draw_particles(d, t):
    for p in PARTS:
        y = (p["y0"] + p["sp"] * t) % (H + 200) - 100
        x = p["x"] + math.sin(t * 1.3 + p["ph"]) * p["sway"]
        if PTYPE == "snow":
            r = p["r"] / 4
            d.ellipse([x - r, y - r, x + r, y + r], fill=p["col"] + (200,)); continue
        ang = p["ph"] + t * p["rot"]; fl = abs(math.cos(t * 1.7 + p["ph"])) * .6 + .4
        ca, sa = math.cos(ang), math.sin(ang)
        d.polygon([(x + px * fl * ca - py * sa, y + px * fl * sa + py * ca) for px, py in shape(p["r"])], fill=p["col"] + (205,))


# ---------- 글자 ----------
def text_center(d, xy, s, f, fill, spacing=0):
    widths = [d.textlength(ch, font=f) for ch in s]
    x = xy[0] - (sum(widths) + spacing * (len(s) - 1)) / 2
    for ch, wch in zip(s, widths):
        d.text((x + 3, xy[1] + 3), ch, font=f, fill=(0, 0, 0, int(fill[3] * .55)), anchor="lm")
        d.text((x, xy[1]), ch, font=f, fill=fill, anchor="lm")
        x += wch + spacing


def overlay(i, lt, d):
    L = SDUR[i]
    if i == 0 and plan.get("title"):
        a = ease((lt - .4) / 1.0) * (1 - ease((lt - (L - 1.6)) / .8))
        if a > 0:
            text_center(d, (W / 2, H * .42 + (1 - ease((lt - .4) / 1.0)) * 40), plan["title"], F_HUGE, (255, 245, 230, int(255 * a)), 18)
            lw = 260 * ease((lt - 1.0) / .8)
            d.line([(W / 2 - lw, H * .53), (W / 2 + lw, H * .53)], fill=ACC + (int(220 * a),), width=3)
            if plan.get("subtitle"):
                b = ease((lt - 1.2) / .8) * (1 - ease((lt - (L - 1.6)) / .8))
                text_center(d, (W / 2, H * .58), plan["subtitle"], F_SUB, (255, 235, 210, int(255 * b)), 10)
    elif i == N - 1 and plan.get("end_title"):
        a = ease((lt - (LEAD[i] + NDUR[i] - 1.0)) / 1.0)
        if a > 0:
            d.rectangle([0, 0, W, H], fill=(20, 10, 10, int(110 * a)))
            text_center(d, (W / 2, H * .40), plan["end_title"], F_HUGE, (255, 240, 220, int(255 * a)), 24)
            if plan.get("end_subtitle"):
                text_center(d, (W / 2, H * .53), plan["end_subtitle"], F_END, ACC + (int(230 * a),), 6)
    elif SC[i].get("label"):
        a = ease((lt - .5) / .7) * (1 - ease((lt - (L - 1.2)) / .6))
        if a > 0:
            x = 120 - (1 - ease((lt - .5) / .7)) * 40
            sub = SC[i].get("sub")
            d.rectangle([x - 28, 118, x - 20, 118 + (190 if sub else 120)], fill=ACC + (int(255 * a),))
            d.text((x + 3, 133), SC[i]["label"], font=F_TITLE, fill=(0, 0, 0, int(140 * a)), anchor="lt")
            d.text((x, 130), SC[i]["label"], font=F_TITLE, fill=(255, 248, 235, int(255 * a)), anchor="lt")
            if sub:
                d.text((x + 4, 268), sub, font=F_SUB, fill=(255, 220, 180, int(255 * a)), anchor="lt")


def wrap(d, txt, f, maxw):
    if d.textlength(txt, font=f) <= maxw:
        return [txt]
    words, lines, cur = txt.split(" "), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f) > maxw and cur:
            lines.append(cur); cur = w_
        else:
            cur = t
    return lines + [cur]


def caption(d, t):
    for s, e, txt in CAPS:
        if s <= t <= e and txt:
            a = min(ease((t - s) / .25), ease((e - t) / .25))
            lines = wrap(d, txt, F_CAP, W - 300)
            tw = max(d.textlength(l, font=F_CAP) for l in lines)
            y0 = H - 120 - (len(lines) - 1) * 66
            d.rounded_rectangle([W / 2 - tw / 2 - 36, y0 - 46, W / 2 + tw / 2 + 36, H - 120 + 42], 18, fill=(0, 0, 0, int(140 * a)))
            for k, l in enumerate(lines):
                d.text((W / 2, y0 + k * 66), l, font=F_CAP, fill=(255, 255, 255, int(255 * a)), anchor="mm")


yy, xx = np.mgrid[0:H, 0:W]
_r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
_v = np.zeros((H, W, 4), np.uint8); _v[..., 3] = (np.clip((_r - .7) / .7, 0, 1) * 150).astype(np.uint8)
VIGNETTE = Image.fromarray(_v, "RGBA")


def frame(t, imgs):
    layers = []
    for i in range(N):
        if starts[i] <= t < starts[i] + SDUR[i]:
            lt = t - starts[i]
            b = camera(imgs[i], i, lt / SDUR[i]).convert("RGBA")
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); overlay(i, lt, ImageDraw.Draw(ov)); b.alpha_composite(ov)
            layers.append((b, lt / XF if (i > 0 and lt < XF) else 1.0))
    out = layers[0][0]
    for im, a in layers[1:]:
        out = Image.blend(out, im, a)
    out.alpha_composite(VIGNETTE)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    draw_particles(d, t); caption(d, t); out.alpha_composite(ov)
    fa = min(1.0, t / 0.6, (TOTAL - t) / 0.8)
    if fa < 1:
        out = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), out, max(fa, 0))
    return out.convert("RGB")


def ts(x):
    ms = int(round(x * 1000)); return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def mix_audio(video, out):
    bgm = find(f"{P}/audio/bgm", (".mp3", ".wav", ".m4a"))
    ins, filt, labels = ["-i", video], [], []
    k = 1
    for i, f in enumerate(NAR):
        if f:
            ins += ["-i", f]; ms = int((starts[i] + LEAD[i]) * 1000)
            filt.append(f"[{k}]loudnorm=I=-18:TP=-2,aresample=44100,aformat=sample_rates=44100:channel_layouts=stereo,adelay={ms}|{ms}[n{k}]"); labels.append(f"[n{k}]"); k += 1
    vol_nar, vol_bgm = plan.get("narration_volume", 1.0), plan.get("bgm_volume", 0.9)
    if labels:
        filt.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,volume={vol_nar},apad=whole_dur={TOTAL}[nar]")
    if bgm:
        ins += ["-i", bgm]
        filt.append(f"[{k}]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:{TOTAL},volume={vol_bgm},"
                    f"afade=t=in:d=1,afade=t=out:st={max(TOTAL - 2.5, 0)}:d=2.5[bg]")
    if bgm and labels:
        filt += ["[nar]asplit[nar1][key]", "[bg][key]sidechaincompress=threshold=0.04:ratio=5:attack=40:release=500[duck]",
                 "[duck][nar1]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]"]
    elif labels:
        filt.append("[nar]alimiter=limit=0.95[a]")
    elif bgm:
        filt.append("[bg]anull[a]")
    else:
        shutil.copy(video, out); return
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL:.3f}", out], check=True)


if __name__ == "__main__":
    imgs = [load_img(i) for i in range(1, N + 1)]
    print(f"장면 길이: {[round(x, 2) for x in SDUR]}  총 {TOTAL:.1f}초")
    if len(sys.argv) > 2 and sys.argv[2] == "preview":
        os.makedirs(f"{P}/frames", exist_ok=True)
        for tt in map(float, sys.argv[3:]):
            frame(tt, imgs).save(f"{P}/frames/p_{tt:05.1f}.jpg", quality=90)
        sys.exit()
    os.makedirs(f"{P}/output", exist_ok=True)
    name = plan.get("output_name", "video")
    tmp = f"{P}/output/_video_tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    n = int(round(TOTAL * FPS))
    for f_ in range(n):
        p.stdin.write(frame(f_ / FPS, imgs).tobytes())
        if f_ % 150 == 0:
            print(f"  {f_}/{n}")
    p.stdin.close(); p.wait()
    if p.returncode != 0:
        sys.exit("영상 인코딩 실패")
    final_tmp = f"{P}/output/_final_tmp.mp4"
    mix_audio(tmp, final_tmp)
    os.replace(final_tmp, f"{P}/output/{name}.mp4"); os.remove(tmp)
    with open(f"{P}/output/{name}.srt", "w", encoding="utf-8") as fp:
        for k, (s, e, txt) in enumerate(CAPS, 1):
            fp.write(f"{k}\n{ts(s)} --> {ts(e)}\n{txt}\n\n")
    print(f"완료: output/{name}.mp4, output/{name}.srt ({TOTAL:.1f}초)")
