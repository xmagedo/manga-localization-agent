# Manga Localization Agent

> ⚠️ **Work in progress.** This repository is being prepared for the
> [CROO Agent Hackathon](https://dorahacks.io/hackathon/croo-hackathon). Interfaces, endpoints, and the
> pipeline are actively changing and are not yet stable.

An agent that localizes Japanese manga pages into other languages (initial
target: **Arabic**). Given a manga page image, it detects speech bubbles,
reads the Japanese text, translates it, and renders the translated text back
onto the page.

## Pipeline (high level)

1. **Speech-bubble & panel detection** — local YOLO models (Ultralytics).
2. **OCR** — Japanese text extraction with [manga-ocr](https://github.com/kha-white/manga-ocr).
3. **Translation** — Japanese → target language (LLM).
4. **Typesetting** — clean the bubble and render reshaped, bidi-correct
   translated text back onto the image (Arabic via `arabic-reshaper` +
   `python-bidi`). *(in progress)*
5. **Delivery manifest** — output image hash, bubble count, timestamps, and
   completed pipeline stages. *(in progress)*

## Status / roadmap

- [x] Bubble + panel detection, OCR, JP→AR translation, JSON/CSV output
- [ ] Single internal `localize(image, target_lang)` entry point
- [ ] Arabic typesetting back onto the page
- [ ] Delivery manifest
- [ ] Job-based API (`POST /localize` → `job_id`, `GET /jobs/{id}`)
- [ ] [croo-sdk](https://docs.croo.network/) provider integration (on-chain settlement)
- [ ] Host model weights publicly (Hugging Face) + auto-download script

## Quick start (local, current state)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then set OPENAI_API_KEY (used for the translation step)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Health check: `curl -s http://localhost:8000/healthz` → `{"status":"ok"}`
API docs: http://localhost:8000/docs

> **Note:** Model weights (`*.pt`) and sample manga pages are **not** included in
> this repository (copyright + size). Provide your own weights and set their
> paths in `.env`.

## License

[MIT](LICENSE) © 2026 xmagedo
