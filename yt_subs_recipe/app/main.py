"""YT Subs → Recipe — FastAPI backend для Home Assistant add-on."""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from pathlib import Path

import aiofiles
import httpx
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="YT Subs → Recipe")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = Path("/downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)
TEMPLATE_FILE = Path("/app/recipe_template.md")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODELS = [
    m.strip()
    for m in os.environ.get(
        "GEMINI_MODELS",
        "gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash",
    ).split(",")
    if m.strip()
]
GEMINI_PROXY = os.environ.get("GEMINI_PROXY") or None
SUB_LANGS = os.environ.get("SUB_LANGS", "ru.*")
COOKIES_FILE = os.environ.get("COOKIES_FILE") or None


# ---------- Ingress middleware ----------

@app.middleware("http")
async def ingress_middleware(request: Request, call_next):
    """HA ingress передаёт префикс пути в X-Ingress-Path."""
    ingress_path = request.headers.get("X-Ingress-Path", "")
    if ingress_path:
        request.scope["root_path"] = ingress_path
    return await call_next(request)


# ---------- Helpers ----------

def extract_video_id(url: str) -> str | None:
    for pat in (
        r"shorts/([a-zA-Z0-9_-]{11})",
        r"watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"embed/([a-zA-Z0-9_-]{11})",
    ):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def clean_srt_text(raw: str) -> str:
    """Убирает таймкоды, номера, теги и дубли из SRT/VTT."""
    raw = re.sub(r"^WEBVTT.*?\n\n", "", raw, flags=re.DOTALL)
    raw = re.sub(r"\d+\n\d{2}:\d{2}:\d{2}[.,]\d{3} --> .*?\n", "", raw)
    raw = re.sub(r"\d{2}:\d{2}:\d{2}[.,]\d{3} --> .*?\n", "", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = re.sub(r"^[a-z-]+:.*$", "", raw, flags=re.MULTILINE)

    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    cleaned: list[str] = []
    for line in lines:
        if not cleaned or cleaned[-1] != line:
            cleaned.append(line)
    return " ".join(cleaned)


async def run_ytdlp(url: str, job_id: str) -> dict:
    outtmpl = str(DOWNLOAD_DIR / f"{job_id}_%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-subs",
        "--write-subs",
        "--sub-langs", SUB_LANGS,
        "--sub-format", "vtt/srt/best",
        "--convert-subs", "srt",
        "--no-playlist",
        "--sleep-requests", "1",
        "--sleep-subtitles", "5",
        "--extractor-retries", "5",
        "--retry-sleep", "429:60",
        "--output", outtmpl,
    ]

    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        cmd += ["--cookies", COOKIES_FILE]

    cmd.append(url)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    stderr_text = stderr.decode(errors="replace")

    print(f"[yt-dlp job={job_id}] rc={proc.returncode}")
    print(f"[yt-dlp job={job_id}] stderr:\n{stderr_text}")

    files = sorted(DOWNLOAD_DIR.glob(f"{job_id}_*"))
    return {
        "job_id": job_id,
        "returncode": proc.returncode,
        "stderr": stderr_text,
        "files": [
            {
                "filename": f.name,
                "size": f.stat().st_size,
                "download_url": f"files/{f.name}",
            }
            for f in files
        ],
    }


RECIPE_PROMPT = """Ты — редактор кулинарных рецептов.
Тебе дан текст из субтитров YouTube Shorts (возможно, с ошибками распознавания речи).
Оформи его как Markdown-рецепт с YAML front matter:
title, description, tags, servings, prep_time, cook_time, total_time,
ingredients (name/amount/unit), steps, notes.
Исправь очевидные ошибки распознавания. Не выдумывай данные, которых нет.
Верни ТОЛЬКО Markdown, без пояснений и без обрамляющих ```.

Текст субтитров:
{text}
"""


async def call_gemini(text: str) -> tuple[str, str]:
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY не задан в настройках add-on")

    prompt = RECIPE_PROMPT.format(text=text)
    last_error: Exception | None = None

    client_kwargs: dict = {"timeout": 60.0}
    if GEMINI_PROXY:
        client_kwargs["proxy"] = GEMINI_PROXY

    async with httpx.AsyncClient(**client_kwargs) as client:
        for model in GEMINI_MODELS:
            for attempt in range(1, 4):
                try:
                    url = (
                        "https://generativelanguage.googleapis.com/v1beta/"
                        f"models/{model}:generateContent?key={GEMINI_API_KEY}"
                    )
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 2000,
                        },
                    }

                    resp = await client.post(url, json=payload)
                    if resp.status_code in (503, 429):
                        raise RuntimeError(f"{resp.status_code}: {resp.text[:200]}")
                    resp.raise_for_status()
                    data = resp.json()

                    markdown = (
                        data["candidates"][0]["content"]["parts"][0]["text"]
                    ).strip()
                    if markdown.startswith("```"):
                        markdown = re.sub(r"^```[a-zA-Z]*\n", "", markdown)
                        markdown = re.sub(r"\n```$", "", markdown)
                    return markdown.strip(), model

                except Exception as e:  # noqa: BLE001
                    last_error = e
                    print(f"[gemini] model={model} attempt={attempt} failed: {e}")
                    if attempt < 3:
                        await asyncio.sleep(2**attempt)

    raise HTTPException(502, f"Все модели недоступны: {last_error}")

# ---------- API ----------

@app.post("/api/download")
async def api_download(url: str = Form(...)):
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(400, "Не удалось извлечь ID видео из URL")

    job_id = uuid.uuid4().hex[:8]
    result = await run_ytdlp(url, job_id)

    if result["returncode"] != 0 and not result["files"]:
        return JSONResponse(
            status_code=502,
            content={
                "error": "yt-dlp завершился с ошибкой",
                "job_id": job_id,
                "stderr": result["stderr"][-3000:],
            },
        )

    return {
        "status": "ok",
        "video_id": video_id,
        "job_id": job_id,
        "files": result["files"],
        "count": len(result["files"]),
    }


@app.post("/api/generate-recipe")
async def generate_recipe(job_id: str = Form(...)):
    files = sorted(
        list(DOWNLOAD_DIR.glob(f"{job_id}_*.srt"))
        + list(DOWNLOAD_DIR.glob(f"{job_id}_*.vtt"))
    )
    if not files:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Субтитры для этого job_id не найдены",
                "job_id": job_id,
                "available_files": sorted(f.name for f in DOWNLOAD_DIR.iterdir()),
            },
        )

    combined_text = ""
    for f in files:
        async with aiofiles.open(f, "r", encoding="utf-8") as fh:
            combined_text += clean_srt_text(await fh.read()) + "\n\n"

    if not combined_text.strip():
        raise HTTPException(400, "Не удалось извлечь текст из субтитров")

    markdown, used_model = await call_gemini(combined_text)

    out_file = DOWNLOAD_DIR / f"{job_id}_recipe.md"
    async with aiofiles.open(out_file, "w", encoding="utf-8") as fh:
        await fh.write(markdown)

    return {
        "status": "ok",
        "job_id": job_id,
        "model": used_model,
        "sources_used": [f.name for f in files],
        "markdown": markdown,
        "file": out_file.name,
        "download_url": f"files/{out_file.name}",
    }


@app.get("/files/{filename}")
async def get_file(filename: str):
    safe = Path(filename).name
    path = DOWNLOAD_DIR / safe
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Файл не найден")

    if safe.endswith(".md"):
        media = "text/markdown; charset=utf-8"
    elif safe.endswith(".srt"):
        media = "application/x-subrip"
    elif safe.endswith(".vtt"):
        media = "text/vtt; charset=utf-8"
    else:
        media = "application/octet-stream"

    return FileResponse(path, media_type=media, filename=safe)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "models": GEMINI_MODELS,
        "proxy": bool(GEMINI_PROXY),
        "api_key": bool(GEMINI_API_KEY),
        "sub_langs": SUB_LANGS,
        "cookies": bool(COOKIES_FILE and os.path.exists(COOKIES_FILE)),
    }


# ---------- Web UI ----------

@app.get("/", response_class=HTMLResponse)
async def index():
    async with aiofiles.open("/app/static/index.html", "r", encoding="utf-8") as f:
        return await f.read()


app.mount("/static", StaticFiles(directory="/app/static"), name="static")