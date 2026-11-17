# gemini-motion-video

주제 하나만 주면 **Gemini API**로 장면 이미지·BGM(Lyria)·나레이션(Gemini TTS)을 만들고, 모션그래픽·자막·음량 합성까지 끝낸 **YouTube용 MP4 + SRT**를 뽑아 주는 Claude Code 스킬입니다.

Google Flow / AI Studio 화면을 조작하지 않고, 같은 계열 모델을 공식 Gemini API로 부릅니다.

## 결과물

- `output/<이름>.mp4` — 1920×1080, 30fps, 켄 번스 카메라 이동, 표지·장소 라벨·마무리 화면, 입자 효과(단풍잎/꽃잎/눈)
- `output/<이름>.srt` — 나레이션 자막
- 음량: 나레이션 -18 LUFS, 나레이션이 나올 때 BGM 자동 덕킹

## 준비

```bash
python --version        # 3.10+
ffmpeg -version         # Windows: winget install Gyan.FFmpeg
pip install google-genai pillow numpy
```

`GEMINI_API_KEY` 환경변수에 [Google AI Studio](https://aistudio.google.com/) API 키를 직접 등록하세요. 키를 파일이나 채팅에 붙여넣지 마세요.

## 설치

이 저장소를 Claude Code 스킬 폴더에 복사합니다.

```bash
git clone https://github.com/jesuswithme/gemini-motion-video ~/.claude/skills/gemini-motion-video
```

## 사용

Claude Code에서:

```
/gemini-motion-video 늦가을 설악산 단풍
```

Claude가 `projects/<slug>/plan.json`(장면·나레이션·이미지 프롬프트)을 만들어 보여 주고, 유료 API 호출 전에 한 번 확인한 뒤 진행합니다.

직접 실행할 수도 있습니다.

```bash
python scripts/generate.py projects/<slug>                              # 이미지·BGM·나레이션 생성 (있는 파일은 건너뜀)
python scripts/make_video.py projects/<slug> preview 2.5 9 15           # 미리보기 프레임
python scripts/make_video.py projects/<slug>                            # 전체 렌더
```

내 사진·음악·녹음을 쓰려면 `images/scene1.jpg …`, `audio/bgm.mp3`, `audio/n1.wav …` 이름으로 미리 넣어 두면 생성 대신 그대로 사용합니다.

모델 이름이 바뀌었다면 환경변수로 바꿀 수 있습니다: `MV_IMAGE_MODEL`, `MV_TTS_MODEL`, `MV_MUSIC_CLIP_MODEL`, `MV_MUSIC_FULL_MODEL`.

## 파일

| 파일 | 내용 |
|---|---|
| `SKILL.md` | 스킬 본문 (작업 순서, plan.json 규칙, 수정 요청 처리) |
| `scripts/generate.py` | Gemini API로 이미지·BGM·나레이션 생성 |
| `scripts/make_video.py` | 모션그래픽 렌더 + 오디오 믹스 + SRT |

API 사용량만큼 Google 요금이 청구됩니다.
