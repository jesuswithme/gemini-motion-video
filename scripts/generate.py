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
