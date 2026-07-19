"""
main.py — 衢小游 FastAPI 后端

API 接口：
  POST /api/chat         — SSE 流式聊天（接收 message + history，返回 event-stream）
  GET  /api/health       — 健康检查
  GET  /api/voice/asr-url — 讯飞 ASR WebSocket 鉴权 URL
  POST /api/voice/tts-url — 讯飞 TTS WebSocket 鉴权 URL + 请求体

启动方式：
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import json
import base64
import hashlib
import hmac
import datetime
from contextlib import asynccontextmanager
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from time import mktime

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chat_engine import chat_stream, init_engine

load_dotenv()

# 讯飞配置
IFLYTEK_APP_ID = os.getenv("IFLYTEK_APP_ID", "")
IFLYTEK_API_KEY = os.getenv("IFLYTEK_API_KEY", "")
IFLYTEK_API_SECRET = os.getenv("IFLYTEK_API_SECRET", "")


# ─────────────────────────────────────────
# 讯飞 WebSocket 鉴权 URL 生成
# ─────────────────────────────────────────
def _assemble_ws_auth_url(request_url: str, api_key: str, api_secret: str, method: str = "GET") -> str:
    host = request_url[request_url.index("://") + 3:]
    path = host[host.index("/"):]
    host = host[:host.index("/")]

    now = datetime.datetime.now()
    date = format_date_time(mktime(now.timetuple()))

    signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature_sha}"'
    )
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode()

    values = {
        "host": host,
        "date": date,
        "authorization": authorization
    }
    return request_url + "?" + urlencode(values)


# ─────────────────────────────────────────
# 生命周期：启动时预加载模型
# ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print("衢小游 — 初始化中...")
    init_engine()
    print("衢小游 — 启动完成，等待请求")
    print("=" * 50)
    yield
    print("衢小游 — 服务关闭")


app = FastAPI(title="衢小游 API", lifespan=lifespan)

# CORS：允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# 请求/响应模型
# ─────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list = []


# ─────────────────────────────────────────
# 健康检查
# ─────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "衢小游"}


# ─────────────────────────────────────────
# SSE 流式聊天
# ─────────────────────────────────────────
@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    SSE 流式聊天接口。

    请求：{"message": "用户消息", "history": [...]}
    响应：text/event-stream

    SSE 事件格式：
      event: message
      data: {"type": "token", "content": "..."}

      event: message
      data: {"type": "tool_call", "name": "plan_route", "status": "calling"}

      event: route
      data: {"origin_coord": "...", "polyline": [...], ...}

      event: message
      data: {"type": "done", "content": "完整回答"}
    """

    def event_generator():
        for event in chat_stream(req.message, req.history):
            event_type = event.get("event", "message")
            data = json.dumps(event.get("data", {}), ensure_ascii=False)
            yield f"event: {event_type}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


# ─────────────────────────────────────────
# 语音 API 请求模型
# ─────────────────────────────────────────
class TTSRequest(BaseModel):
    text: str


# ─────────────────────────────────────────
# 讯飞 ASR 语音识别 WebSocket 鉴权 URL
# ─────────────────────────────────────────
@app.get("/api/voice/asr-url")
async def get_asr_url():
    """
    返回讯飞语音听写（ASR）WebSocket 鉴权 URL + appId。
    前端通过该 URL 建立 WebSocket，发送音频流，接收识别结果。
    """
    if not IFLYTEK_APP_ID or not IFLYTEK_API_KEY or not IFLYTEK_API_SECRET:
        return {"error": "未配置讯飞 API 密钥，请检查 .env 文件"}

    ws_url = _assemble_ws_auth_url(
        request_url="wss://iat-api.xfyun.cn/v2/iat",
        api_key=IFLYTEK_API_KEY,
        api_secret=IFLYTEK_API_SECRET,
        method="GET",
    )
    return {"url": ws_url, "appId": IFLYTEK_APP_ID}


# ─────────────────────────────────────────
# 讯飞 TTS 语音合成 WebSocket 鉴权 URL + 请求体
# ─────────────────────────────────────────
@app.post("/api/voice/tts-url")
async def get_tts_url(req: TTSRequest):
    """
    返回讯飞语音合成（TTS）WebSocket 鉴权 URL + 请求体。
    前端通过该 URL 建立 WebSocket，发送请求体，接收合成音频。
    """
    if not IFLYTEK_APP_ID or not IFLYTEK_API_KEY or not IFLYTEK_API_SECRET:
        return {"error": "未配置讯飞 API 密钥，请检查 .env 文件"}

    ws_url = _assemble_ws_auth_url(
        request_url="wss://tts-api.xfyun.cn/v2/tts",
        api_key=IFLYTEK_API_KEY,
        api_secret=IFLYTEK_API_SECRET,
        method="GET",
    )

    body = {
        "common": {"app_id": IFLYTEK_APP_ID},
        "business": {
            "aue": "lame",
            "auf": "audio/L16;rate=16000",
            "vcn": "xiaoyan",
            "tte": "utf8",
            "speed": 50,
            "volume": 50,
            "pitch": 50,
        },
        "data": {
            "text": base64.b64encode(req.text.encode('utf-8')).decode('utf-8'),
            "status": 2,
        },
    }
    return {"url": ws_url, "body": body}


# ─────────────────────────────────────────
# 入口
# ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)