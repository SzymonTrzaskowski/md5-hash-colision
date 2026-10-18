"""Local web UI for the MD5 collision demo."""

from __future__ import annotations

import base64
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.collision import build_file_pair, build_picture_pair

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"
DOC_PATH = ROOT / "docs" / "how-md5-broke.md"

app = FastAPI(title="MD5 collision demo")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SharedText(BaseModel):
    text: str = Field(default="", max_length=20000)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/how-md5-broke", response_class=HTMLResponse)
def how_md5_broke() -> str:
    return _article_page(_markdown_to_html(DOC_PATH.read_text(encoding="utf-8")))


@app.post("/api/pictures")
async def pictures(
    first: UploadFile = File(...),
    second: UploadFile = File(...),
) -> dict:
    try:
        result = build_picture_pair(await first.read(), await second.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _public(result)


@app.post("/api/files")
def files(body: SharedText) -> dict:
    try:
        result = build_file_pair(body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _public(result)


def _public(result: dict) -> dict:
    files = []
    for item in result["files"]:
        files.append(
            {
                "name": item["name"],
                "media_type": item["media_type"],
                "size": item["size"],
                "sha256": item["sha256"],
                "base64": base64.b64encode(item["data"]).decode("ascii"),
            }
        )
    return {
        "md5": result["md5"],
        "kind": result["kind"],
        "files": files,
        "diff": result["diff"],
        "blocks": result["blocks"],
    }


def _article_page(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>How MD5 was broken</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <article class="sheet">
    <p class="eyebrow"><a href="/">MD5 collision demo</a></p>
    {body}
  </article>
</body>
</html>
"""


def _markdown_to_html(source: str) -> str:
    """Render the small subset of Markdown used by the write-up."""
    html: list[str] = []
    paragraph: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            html.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html.append("</ul>")
            in_list = False

    for raw in source.splitlines():
        line = raw.rstrip()
        if in_code:
            if line.strip() == "```":
                html.append("<pre><code>" + "\n".join(code_lines) + "</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                code_lines.append(_escape(line))
            continue
        if line.strip() == "```":
            flush_paragraph()
            close_list()
            in_code = True
            continue
        if not line.strip():
            flush_paragraph()
            close_list()
            continue
        if line.startswith("### "):
            flush_paragraph()
            close_list()
            html.append(f"<h3>{_inline(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            flush_paragraph()
            close_list()
            html.append(f"<h2>{_inline(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            flush_paragraph()
            close_list()
            html.append(f"<h1>{_inline(line[2:])}</h1>")
            continue
        if line.startswith("- "):
            flush_paragraph()
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f"<li>{_inline(line[2:])}</li>")
            continue
        close_list()
        paragraph.append(line.strip())
    flush_paragraph()
    close_list()
    return "\n".join(html)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _inline(text: str) -> str:
    escaped = _escape(text)
    parts: list[str] = []
    while "`" in escaped:
        before, _, rest = escaped.partition("`")
        code, _, escaped = rest.partition("`")
        parts.append(before)
        parts.append(f"<code>{code}</code>")
    parts.append(escaped)
    return "".join(parts)
