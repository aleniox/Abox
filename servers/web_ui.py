import asyncio
import logging
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from modules.agent.agent_main import process_message, SEARCH_RESULTS

logger = logging.getLogger(__name__)

app = FastAPI(title="J.A.R.V.I.S. Web UI")

app.mount("/static", StaticFiles(directory="bots/bothub"), name="static")


@app.get("/")
async def index():
    with open("bots/bothub/jarvis_hud_interface.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket connected")

    await ws.send_json({"type": "status", "text": "Kết nối J.A.R.V.I.S. thành công."})

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg = data.get("message", "").strip()
            if not msg:
                continue

            logger.info(f"[WS] message: {msg[:100]}")

            await ws.send_json({"type": "status", "text": "Đang xử lý..."})

            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(
                    None, process_message, msg, 1
                )
                text = result if isinstance(result, str) else result.get("text", str(result))

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
                await ws.send_json({
                    "type": "response",
                    "text": text,
                    "search_results": search_results if search_results else None
                })
            except Exception as e:
                logger.exception(f"[WS] error: {e}")
                await ws.send_json({
                    "type": "response",
                    "text": f"Xin lỗi thưa Ngài starkling, đã xảy ra lỗi: {str(e)}",
                    "search_results": None
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception(f"[WS] unexpected error: {e}")
