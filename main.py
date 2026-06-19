"""
main.py — 衢小游 FastAPI 后端

API 接口：
  POST /api/chat    — SSE 流式聊天（接收 message + history，返回 event-stream）
  GET  /api/health  — 健康检查

启动方式：
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chat_engine import chat_stream, init_engine


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
# 入口
# ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
