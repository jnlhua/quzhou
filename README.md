# 衢小游 — 衢州旅游 AI 助手

基于 **DeepSeek + RAG + Agent** 的衢州旅游智能问答系统，支持天气查询、路线规划、景点推荐、美食搜索等功能，集成语音交互（ASR/TTS）、高德地图路线可视化、RAG 检索评估体系。

## 项目架构

```
quzhou/
├── main.py                  # FastAPI 后端入口，SSE 流式聊天 + 语音鉴权 API
├── chat_engine.py           # 对话引擎：Agent + RAG + LLM（ReAct 循环 + 问题改写）
├── agent.py                 # 工具模块：天气/路线/POI/地理编码（高德 API）
├── evaluate.py              # RAG 检索评估脚本（5 种策略对比）
├── Download.py              # 模型下载脚本（BGE-M3 / BGE-Reranker）
├── requirements.txt         # Python 依赖清单
├── .env.example             # 环境变量示例
├── data/
│   ├── raw/                 # 原始知识库（Markdown）
│   │   ├── food.md          # 衢州美食
│   │   ├── jianglangshan.md # 江郎山景区
│   │   ├── lankeshan.md     # 烂柯山景区
│   │   ├── transport.md     # 交通信息
│   │   ├── accommodation.md # 住宿推荐
│   │   ├── festivals.md     # 节庆活动
│   │   ├── shopping.md      # 购物特产
│   │   └── gengong_shuitingmen.md  # 根宫佛国/水亭门
│   ├── processed/
│   │   └── chunks_final.json # RAG 知识库分块（33 条）
│   └── chroma_db/           # ChromaDB 向量数据库
└── frontend/                # Vue 3 前端
    ├── index.html           # 入口 HTML（集成高德地图 JS SDK）
    └── src/
        ├── App.vue          # 主界面（SSE 流式接收 + 地图联动）
        ├── components/
        │   ├── MessageBubble.vue  # 消息气泡（思考步骤 + 改写提示）
        │   └── MapPanel.vue       # 高德地图面板（路线绘制）
        └── composables/
            └── useVoice.js        # 语音交互（讯飞 ASR + TTS）
```

## 核心功能

| 功能 | 说明 |
|------|------|
| 智能问答 | 基于 RAG 技术，从知识库检索衢州旅游信息并生成回答 |
| 多步 Agent | ReAct 循环（最多 3 轮），AI 自主决定是否调用工具、调用几个 |
| 天气查询 | 调用高德天气 API，获取实时天气 + 4 日预报 |
| 路线规划 | 调用高德路线规划 API，支持驾车/步行，前端地图可视化 |
| POI 搜索 | 搜索衢州周边餐厅、酒店、景点等兴趣点 |
| 问题改写 | 检索失败时自动改写用户问题，提高召回率 |
| 思考步骤 | 前端实时展示 AI 的推理过程（调用工具 → 获取结果 → 生成回答） |
| 语音交互 | 讯飞 ASR 语音识别 + TTS 语音播报 |
| 流式输出 | SSE 流式传输，打字机效果逐字显示回答 |
| 安全过滤 | 输入清洗 + Prompt 注入防护，最多 500 字限制 |
| 检索评估 | 内置评估脚本，对比 5 种检索策略的 Hit@K / MRR 指标 |

## 技术栈

### 后端

- **Web 框架**：FastAPI + Uvicorn
- **大模型**：DeepSeek Chat API（Function Calling）
- **向量模型**：BAAI/bge-m3（Embedding）+ BAAI/bge-reranker-base（重排序）
- **检索策略**：语义检索 + BM25 关键词检索 → RRF 融合 → Reranker 精排
- **向量数据库**：ChromaDB
- **地图服务**：高德地图 API（天气/地理编码/路线规划/POI 搜索）
- **语音服务**：讯飞开放平台（ASR 语音听写 + TTS 语音合成，WebSocket 协议）

### 前端

- **框架**：Vue 3 + Vite
- **Markdown 渲染**：marked
- **地图**：高德地图 JS API 2.0（路线绘制 + Marker）
- **语音采集**：Web Audio API（PCM 采集 + 降采样 → 讯飞 WebSocket）

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- 高德地图 API Key（[申请地址](https://lbs.amap.com/)）
- DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）

### 1. 克隆项目

```bash
git clone https://github.com/jnlhua/quzhou.git
cd quzhou
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-key
AMAP_API_KEY=your-amap-key
AMAP_JS_KEY=your-amap-js-key
AMAP_JS_SECURITY_KEY=your-amap-js-security-key
IFLYTEK_APP_ID=your-iflytek-app-id
IFLYTEK_API_KEY=your-iflytek-api-key
IFLYTEK_API_SECRET=your-iflytek-api-secret
```

### 3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 4. 下载嵌入模型

```bash
python Download.py
```

> 模型将下载到 `./models/BAAI/` 目录，首次运行需联网，约 2GB。

### 5. 启动后端

```bash
python main.py
```

后端服务默认运行在 `http://localhost:8000`。

### 6. 启动前端（可选）

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器运行在 `http://localhost:5173`。

## API 接口

### `GET /api/health`

健康检查接口。

**响应示例：**

```json
{
  "status": "ok",
  "service": "衢小游"
}
```

### `POST /api/chat`

SSE 流式聊天接口。

**请求体：**

```json
{
  "message": "明天衢州天气怎么样？",
  "history": [
    { "role": "user", "content": "你好" },
    { "role": "assistant", "content": "你好！我是衢小游..." }
  ]
}
```

**SSE 事件类型：**

| 事件 | 说明 |
|------|------|
| `event: message` / `type: token` | 流式文本片段 |
| `event: message` / `type: tool_call` | 工具调用状态通知 |
| `event: step` | AI 思考步骤（调用工具/获取结果/生成回答） |
| `event: rewrite` | 问题改写提示（原始问题 + 改写后问题） |
| `event: route` | 路线规划结果（含坐标和路径） |
| `event: message` / `type: done` | 对话结束 |

## 知识库说明

知识库位于 `data/raw/` 目录，以 Markdown 格式存储，包含以下内容：

- **江郎山**：门票价格、交通方式、核心景点（三爿石、十八曲古道等）
- **烂柯山**：门票价格、围棋文化、交通路线
- **美食**：烂柯卤水、龙游发糕、常山胡柚、开化清水鱼、烤饼等
- **交通**：市内公交、长途客运、高速路网

知识库分块存储在 `data/processed/chunks_final.json`，首次启动时自动构建 ChromaDB 向量索引。

## 工作流程

```
用户提问 → 安全过滤（注入检测 + 长度限制）
         ↓
    DeepSeek（带 tools，ReAct 循环，最多 3 轮）
    ├── 触发 tool_call → 执行工具 → 结果喂回 → AI 判断是否需要继续
    │   └── 循环直到信息充分或达到上限
    └── 无 tool_call → RAG 检索
         ├── 检索成功（rerank_score >= 阈值）→ 注入上下文 → 生成回答
         └── 检索失败 → 问题改写 → 重新检索 → 成功则提示"您可能是想问"
         ↓
    SSE 流式输出（思考步骤 + 打字机效果 + 地图路线）
```

> **身份约束**：System Prompt 中明确限定衢小游只回答衢州旅游相关问题，非衢州话题会被礼貌拒绝。  
> **历史截断**：多轮对话最多保留最近 10 条历史记录，避免 Token 超限和 API 费用膨胀。

## 路线规划特殊处理

当用户询问路线规划时，系统会：

1. 调用高德路线规划 API 获取驾车/步行路线
2. 提取完整路径坐标串（polyline）
3. 通过 `event: route` SSE 事件推送坐标数据
4. 前端高德地图自动绘制路线

## 安全措施

- **输入长度限制**：单次最多 500 字，防止恶意超长输入
- **Prompt 注入检测**：正则匹配常见注入模式（如 `ignore previous instructions`、角色扮演、越狱指令等），命中则拒绝
- **隐藏字符清洗**：过滤零宽字符（`\u200b` 等）和异常的连续换行

## RAG 检索评估

内置评估脚本 `evaluate.py`，包含 23 条测试用例（覆盖简单问题、口语化表述、模糊意图），对比 5 种检索策略：

```bash
python evaluate.py
```

| 策略 | Hit@1 | Hit@3 | MRR |
|------|-------|-------|-----|
| 纯语义检索（BGE-M3） | 21.7% | 39.1% | 0.283 |
| 纯 BM25 关键词 | 34.8% | 69.6% | 0.500 |
| 双路 RRF 融合 | 30.4% | 56.5% | 0.428 |
| **双路 + Reranker 精排** | **60.9%** | **69.6%** | **0.652** |
| 完整管线 + 问题改写 | 60.9% | 69.6% | 0.652 |

> Reranker 精排将 Hit@1 从 30.4% 提升至 60.9%，是管线中提升最大的环节。

## 开源协议

本项目采用 **MIT 协议** 开源。简单来说：任何人都可以自由使用、修改、分发这份代码，不管是个人学习还是商业用途，只需保留原作者版权声明即可。详情见 [MIT 协议全文](https://mit-license.org/)。