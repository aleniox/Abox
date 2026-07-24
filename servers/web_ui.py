import asyncio
import json
import logging
import os
import re
import socket

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response

from modules.agent.agent_main import process_message, SEARCH_RESULTS
from modules.core.speech2text import transcribe_api_whisper

logger = logging.getLogger(__name__)

app = FastAPI(title="J.A.R.V.I.S. Web UI")

app.mount("/static", StaticFiles(directory="bots/bothub"), name="static")


@app.get("/")
async def index():
    with open("bots/bothub/jarvis_hud_interface.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    model: str = Form("convert-model-880000"),
    language: str = Form("vi"),
    task: str = Form("transcribe"),
    batch_size: int = Form(8),
    chunk_size: int = Form(15),
    compute_type: str = Form("float16"),
):
    audio_data = await audio.read()
    text = await transcribe_api_whisper(
        audio_data, audio.filename or "audio.wav",
        model, language, task, batch_size, chunk_size, compute_type
    )
    return {"text": text, "language": language}


# Suppress Windows Proactor ConnectionResetError on WS disconnect
def _suppress_ws_reset(loop, context):
    exc = context.get("exception")
    if isinstance(exc, (ConnectionResetError, ConnectionAbortedError)):
        return
    loop.default_exception_handler(context)


loop = asyncio.get_event_loop()
loop.set_exception_handler(_suppress_ws_reset)


@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket connected")

    await ws.send_json({"type": "status", "text": "Kết nối J.A.R.V.I.S. thành công."})

    try:
        while True:
            try:
                raw = await ws.receive_text()
            except (WebSocketDisconnect, ConnectionResetError, RuntimeError):
                break
            data = json.loads(raw)
            msg = data.get("message", "").strip()
            if not msg:
                continue

            logger.info(f"[WS] message: {msg[:100]}")

            await ws.send_json({"type": "status", "text": "Đang xử lý..."})

            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(
                    None, process_message, msg, 1, None, None, None, "", "webui"
                )
                raw_text = result if isinstance(result, str) else result.get("text", str(result))
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group(0))
                        text = parsed.get("dialogue", raw_text)
                    except json.JSONDecodeError:
                        text = raw_text
                else:
                    text = raw_text

                # Collect structured search results if available
                search_results = []
                if SEARCH_RESULTS.get(1):
                    seen = set()
                    for r in SEARCH_RESULTS[1]:
                        key = r.get("url", "")
                        if key and key not in seen:
                            seen.add(key)
                            search_results.append(r)

                logger.info(f"[WS] response ({len(text)} chars) + {len(search_results)} search results")
                try:
                    await ws.send_json({
                        "type": "response",
                        "text": text,
                        "search_results": search_results if search_results else None
                    })
                except RuntimeError:
                    logger.warning("[WS] Client đã ngắt kết nối trước khi gửi response")
            except Exception as e:
                logger.exception(f"[WS] error: {e}")
                try:
                    await ws.send_json({
                        "type": "response",
                        "text": f"Xin lỗi thưa Ngài starkling, đã xảy ra lỗi: {str(e)}",
                        "search_results": None
                    })
                except RuntimeError:
                    logger.warning("[WS] Client đã ngắt kết nối khi gửi error response")

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception(f"[WS] unexpected error: {e}")
