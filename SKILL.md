---
name: "gemini-motion-video"
description: "Claude Code에서 주제만 받아 Gemini API(이미지·Lyria BGM·Gemini TTS 나레이션)로 소재를 자동 생성하고 자막·모션그래픽을 입힌 YouTube용 MP4와 SRT를 만든다. 풍경·계절·여행 모션그래픽 영상 요청 시 사용."
---

# Gemini 모션그래픽 영상 (Claude Code 전용)

주제 하나로 **장면 구성 → 이미지·BGM·나레이션 생성(Gemini API) → 모션그래픽·자막·음량 합성 → MP4 + SRT**까지 자동으로 만든다.
Google Flow / Flow Music / AI Studio 화면을 조작하지 않는다. 같은 계열 모델(이미지 모델, Lyria, Gemini TTS)을 공식 Gemini API로 부른다.

## 0. 사전 준비 (처음 한 번)

1. 확인: `python --version`(3.10+), `ffmpeg -version`, `ffprobe -version`. 없으면 설치 방법을 안내한다 (Windows: `winget install Gyan.FFmpeg`).
2. 패키지: `pip install google-genai pillow numpy`
3. API 키: `GEMINI_API_KEY` 환경변수가 있는지만 확인한다 (`echo %GEMINI_API_KEY%` 또는 `echo $GEMINI_API_KEY`가 비어있지 않은지).
   - **키 값을 출력·기록·채팅에 붙여넣거나 파일에 쓰지 않는다.** 없으면 사용자에게 AI Studio에서 키를 만들어 직접 환경변수로 등록하도록 안내하고 멈춘다.
4. 스크립트: 이 스킬 폴더의 `scripts/generate.py`, `scripts/make_video.py`가 없으면 아래 '부록'의 코드 그대로 만들어 둔다.

## 1. 입력 받기

- 필수: **주제**
- 선택(없으면 기본값): 길이(30초), 장면 수(5), 목소리(Charon, 차분한 다큐 톤), 입자 효과(주제에 맞게: 가을 maple / 봄 petal / 겨울 snow / 그 외 none), 출력 파일 이름.
- 사용자가 직접 만든 소재가 있으면 그대로 쓴다 (아래 4번 참고). 묻기보다 기본값으로 진행하고, 선택한 값을 계획서에 적는다.

## 2. 계획서 만들기 → `projects/<slug>/plan.json`

```json
{
  "topic": "늦가을 설악산 단풍",
  "output_name": "seorak_autumn",
  "target_seconds": 30,
  "title": "설악, 붉게 물들다",
  "subtitle": "늦가을 단풍 여행",
  "end_title": "설악산",
  "end_subtitle": "SEORAKSAN · LATE AUTUMN",
  "particles": "maple",
  "accent": [240, 120, 40],
  "image_style": "photorealistic landscape photography, cinematic, rich autumn colors",
  "music_prompt": "Peaceful cinematic autumn ambient, gentle gayageum plucks with soft piano and warm strings, 70 BPM, nostalgic and calm, soft fade-out ending",
  "voice": {"name": "Charon", "style": "한국어 자연 다큐멘터리 나레이터처럼 차분하고 따뜻하게, 약간 느린 속도로 읽어주세요."},
  "scenes": [
    {"narration": "늦가을, 설악이 가장 붉게 타오르는 시간.", "image_prompt": "Aerial view of Seoraksan ridges in late autumn, morning mist in valleys, warm sunrise", "camera": "in"},
    {"label": "대청봉", "sub": "해발 1,708m", "narration": "대청봉에서 시작된 단풍이 능선을 타고 천천히 내려옵니다.", "image_prompt": "...", "camera": "out"}
  ]
}
```

작성 규칙:
- 장면 1은 `title`/`subtitle` 표지, 마지막 장면은 `end_title`/`end_subtitle` 마무리 화면이 자동으로 뜬다. 가운데 장면만 `label`(장소 이름)과 `sub`(보조 정보)를 쓴다.
- **나레이션 길이**: 한국어 1문장, 약 15~22음절 (읽는 시간 4~5초). 30초면 5문장. 장면 길이는 실제 음성 길이에 맞춰 자동 계산된다.
- `sub`의 숫자(해발, 연도 등)는 사실이어야 한다. 확실하지 않으면 빼거나 웹에서 확인한다.
- `image_prompt`는 영어. 장면마다 시점·시간대·구도를 다르게 (항공 뷰 / 클로즈업 / 노을 / 숲길 등). 글자·사람 얼굴 클로즈업 금지.
- `camera`: in, out, left, right, up, down 중 장면마다 섞는다.
- `music_prompt`: 장르·악기·BPM·분위기·끝맺음. 30초 이하면 Lyria clip 모델(항상 30초)을 쓴다.
- 목소리 후보: Charon(차분한 해설), Gacrux(중후), Sulafat·Vindemiatrix(따뜻한 여성).

## 3. 사용자 확인 (한 번만)

계획서를 표로 보여준다 (장면 / 화면 이름 / 나레이션 / 이미지 요약). 그리고 **유료 API 호출 전에 한 번 묻는다**:
"이미지 N장 + BGM 1곡 + 나레이션 N개를 Gemini API로 생성할까요? (사용량만큼 API 요금이 청구됩니다)"
사용자가 처음 요청에서 이미 "바로 만들어" / "확인 없이"라고 했다면 묻지 않는다.

## 4. 소재 생성

```
python scripts/generate.py projects/<slug>
```
- 이미 있는 파일은 건너뛴다. 사용자가 준 소재는 이 이름으로 먼저 넣어두면 그대로 쓰인다:
  `images/scene1.png|jpg … sceneN`, `audio/bgm.mp3|wav|m4a`, `audio/n1.wav|mp3|m4a … nN`.
- 사용자 나레이션이 한 파일이면 ffmpeg `silencedetect`(-40dB, 0.5초)로 문장 사이를 찾아 n1..nN으로 자른다. 잘라낼 때는 먼저 wav로 변환하고, 입력 앞에 `-ss`를 둔다. 경계가 애매하면 사용자에게 그 위치를 들어보라고 말한다.
- 특정 소재만 다시: `--only images|music|voice --force` (해당 파일을 지우고 실행해도 된다).
- 모델 이름 오류(404 / not found)가 나면 `client.models.list()`로 현재 이름을 찾아 환경변수로 바꾼다: `MV_IMAGE_MODEL`, `MV_TTS_MODEL`, `MV_MUSIC_CLIP_MODEL`, `MV_MUSIC_FULL_MODEL`.
- 안전 필터로 이미지가 안 나오면 그 장면 프롬프트를 순화해서 그 장면만 다시 만든다.

## 5. 미리보기 프레임 확인 (전체 렌더 전에 반드시)

```
python scripts/make_video.py projects/<slug> preview 2.5 <장면2 중간> <마지막-1.5>
```
`frames/*.jpg`를 직접 열어 본다. 확인할 것: 글자가 배경에 묻히지 않는지, 이미지에 이상한 글자·워터마크·왜곡이 없는지, 자막이 화면 밖으로 넘치지 않는지. 문제가 있으면 이미지를 다시 만들거나 `camera`·`accent`를 바꾼 뒤 다시 본다.

## 6. 전체 렌더 (한 번)

```
python scripts/make_video.py projects/<slug>
```
→ `output/<output_name>.mp4` (1920×1080, 30fps), `output/<output_name>.srt`
- 음량: 나레이션은 -18 LUFS로 맞추고, 나레이션이 나올 때 BGM이 자동으로 작아진다. 조정은 plan.json의 `bgm_volume`(기본 0.9), `narration_volume`(기본 1.0).
- 확인: `ffprobe`로 길이를 보고, `volumedetect`로 max_volume이 0dB 미만인지 본다.

## 7. 마무리 보고

결과 파일 경로, 총 길이, 쓴 목소리와 BGM 모델을 짧게 알린다. 그리고 수정할 수 있는 것을 한 줄로 안내한다 (특정 장면 이미지 재생성 / 목소리 변경 / 길이 조정).
영상에 자막이 이미 있으므로, SRT를 YouTube에 올린다면 기본으로 꺼두라고 알려준다.

## 수정 요청 처리

- 이미지 1장 교체: 해당 `images/sceneK.*` 삭제 → `generate.py --only images` → 6번.
- 문장 수정: plan.json 수정 → 해당 `audio/nK.*` 삭제 → `--only voice` → 6번.
- BGM 교체: `audio/bgm.*` 삭제 → `--only music` (또는 사용자 파일 넣기) → 6번.

---

## 부록 A: scripts/generate.py

```python
"""Gemini API로 장면 이미지, BGM, 나레이션을 만든다.
사용: python generate.py <project_dir> [--only images|music|voice] [--force]
필요: GEMINI_API_KEY 환경변수, pip install google-genai
이미 있는 파일(사용자가 넣은 소재 포함)은 --force 없이는 건너뛴다.
"""
import json, os, sys, time, wave, subprocess, argparse
from google import genai
from google.genai import types

IMAGE_MODEL = os.environ.get("MV_IMAGE_MODEL", "gemini-2.5-flash-image")
TTS_MODEL = os.environ.get("MV_TTS_MODEL", "gemini-2.5-flash-preview-tts")
MUSIC_CLIP_MODEL = os.environ.get("MV_MUSIC_CLIP_MODEL", "lyria-3-clip-preview")
MUSIC_FULL_MODEL = os.environ.get("MV_MUSIC_FULL_MODEL", "lyria-3.5")


def retry(fn, what, tries=4):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            if i == tries - 1 or not any(k in msg for k in ("429", "503", "500", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "DEADLINE")):
                raise RuntimeError(f"{what} 실패: {msg}") from e
            wait = 10 * (i + 1)
            print(f"  {what}: 일시 오류, {wait}초 후 재시도 ({msg[:80]})")
            time.sleep(wait)


def exists_any(base, exts):
    return next((base + e for e in exts if os.path.exists(base + e)), None)


def gen_images(client, P, plan, force):
    os.makedirs(f"{P}/images", exist_ok=True)
    style = plan.get("image_style", "photorealistic, cinematic, natural light")
    for i, sc in enumerate(plan["scenes"], 1):
        base = f"{P}/images/scene{i}"
        if not force and exists_any(base, (".png", ".jpg", ".jpeg", ".webp")):
            print(f"  scene{i} 이미지 있음, 건너뜀"); continue
        prompt = f"{sc['image_prompt']}. {style}. Wide 16:9 landscape composition, no text, no watermark, no people's faces in close-up."
        def call():
            return client.models.generate_content(
                model=IMAGE_MODEL, contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="16:9")))
        r = retry(call, f"scene{i} 이미지")
        data = next((p.inline_data.data for p in r.parts if p.inline_data is not None), None)
        if not data:
            raise RuntimeError(f"scene{i}: 이미지가 반환되지 않음 (안전 필터일 수 있음). 프롬프트를 바꿔 다시 실행")
        mime = next(p.inline_data.mime_type for p in r.parts if p.inline_data is not None)
        ext = ".jpg" if "jpeg" in (mime or "") else ".png"
        open(base + ext, "wb").write(data)
        print(f"  scene{i}{ext} 저장")


def gen_music(client, P, plan, force):
    os.makedirs(f"{P}/audio", exist_ok=True)
    if not force and exists_any(f"{P}/audio/bgm", (".mp3", ".wav", ".m4a")):
        print("  BGM 있음, 건너뜀"); return
    target = plan.get("target_seconds", 30)
    model = MUSIC_CLIP_MODEL if target <= 30 else MUSIC_FULL_MODEL
    prompt = plan["music_prompt"]
    if "instrumental" not in prompt.lower():
        prompt += " Instrumental only, no vocals."
    if model == MUSIC_FULL_MODEL:
        prompt += f" Create a {int(target) + 10}-second piece."
    r = retry(lambda: client.models.generate_content(model=model, contents=prompt), "BGM")
    data = next((p.inline_data.data for p in r.parts if p.inline_data is not None), None)
    if not data:
        raise RuntimeError("BGM 오디오가 반환되지 않음")
    open(f"{P}/audio/bgm.mp3", "wb").write(data)
    print(f"  bgm.mp3 저장 ({model})")


def trim_silence(src, dst):
    af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
          "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
          "afade=t=in:d=0.03,loudnorm=I=-18:TP=-2:LRA=11")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", af, "-ar", "44100", dst], check=True)


def gen_voice(client, P, plan, force):
    os.makedirs(f"{P}/audio", exist_ok=True)
    v = plan.get("voice", {})
    name = v.get("name", "Charon")
    style = v.get("style", "Read in Korean like a calm, warm nature documentary narrator, slightly slow pace.")
    for i, sc in enumerate(plan["scenes"], 1):
        out = f"{P}/audio/n{i}.wav"
        if not sc.get("narration"):
            continue
        if not force and exists_any(f"{P}/audio/n{i}", (".wav", ".mp3", ".m4a")):
            print(f"  n{i} 있음, 건너뜀"); continue
        text = f"{style}\n\n{sc['narration']}"
        def call():
            return client.models.generate_content(
                model=TTS_MODEL, contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=name)))))
        r = retry(call, f"n{i} 나레이션")
        pcm = next((p.inline_data.data for p in r.parts if p.inline_data is not None), None)
        if not pcm:
            raise RuntimeError(f"n{i}: 음성이 반환되지 않음")
        raw = f"{P}/audio/_n{i}_raw.wav"
        with wave.open(raw, "wb") as w:  # Gemini TTS: 24kHz 16-bit mono PCM
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
        trim_silence(raw, out)
        os.remove(raw)
        print(f"  n{i}.wav 저장")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project"); ap.add_argument("--only", choices=["images", "music", "voice"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        sys.exit("GEMINI_API_KEY 환경변수가 없습니다. AI Studio에서 키를 만들어 직접 설정해 주세요.")
    plan = json.load(open(f"{a.project}/plan.json", encoding="utf-8"))
    client = genai.Client()
    if a.only in (None, "images"): print("이미지 생성"); gen_images(client, a.project, plan, a.force)
    if a.only in (None, "music"): print("BGM 생성"); gen_music(client, a.project, plan, a.force)
    if a.only in (None, "voice"): print("나레이션 생성"); gen_voice(client, a.project, plan, a.force)
    print("완료")
```

## 부록 B: scripts/make_video.py

```python
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
```