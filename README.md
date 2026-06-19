# 衢小游 — 衢州旅游 AI 助手

基于 **DeepSeek + RAG + Agent** 的衢州旅游智能问答系统，支持天气查询、路线规划、景点推荐、美食搜索等功能，前端集成高德地图实现路线可视化。

## 项目架构

```
quzhou/
├── main.py                  # FastAPI 后端入口，SSE 流式聊天 API
├── chat_engine.py           # 对话引擎：Agent + RAG + LLM（ReAct 循环）
├── agent.py                 # 工具模块：天气/路线/POI/地理编码（高德 API）
├── Download.py              # 模型下载脚本（BGE-M3 / BGE-Reranker）
├── requirements.txt         # Python 依赖清单
├── .env.example             # 环境变量示例
├── data/
│   ├── raw/                 # 原始知识库（Markdown）
│   │   ├── food.md          # 衢州美食
│   │   ├── jianglangshan.md # 江郎山景区
│   │   ├── lankeshan.md     # 烂柯山景区
│   │   └── transport.md     # 交通信息
│   ├── processed/
│   │   └── chunks.json      # RAG 知识库分块
│   └── chroma_db/           # ChromaDB 向量数据库
└── frontend/                # Vue 3 前端
    ├── index.html           # 入口 HTML（集成高德地图 JS SDK）
    └── dist/                # 生产构建产物
```

## 核心功能

| 功能 | 说明 |
|------|------|
| 智能问答 | 基于 RAG 技术，从知识库检索衢州旅游信息并生成回答 |
| 天气查询 | 调用高德天气 API，获取实时天气 + 4 日预报 |
| 路线规划 | 调用高德路线规划 API，支持驾车/步行，前端地图可视化 |
| POI 搜索 | 搜索衢州周边餐厅、酒店、景点等兴趣点 |
| 流式输出 | SSE 流式传输，打字机效果逐字显示回答 |
| 安全过滤 | 输入清洗 + Prompt 注入防护，最多 500 字限制 |

## 技术栈

### 后端

- **Web 框架**：FastAPI + Uvicorn
- **大模型**：DeepSeek Chat API（Function Calling）
- **向量模型**：BAAI/bge-m3（Embedding）+ BAAI/bge-reranker-base（重排序）
- **检索策略**：语义检索 + BM25 关键词检索 → RRF 融合 → Reranker 精排
- **向量数据库**：ChromaDB
- **地图服务**：高德地图 API（天气/地理编码/路线规划/POI 搜索）

### 前端

- **框架**：Vue 3 + Vite
- **Markdown 渲染**：marked
- **地图**：高德地图 JS API 2.0（路线绘制）

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
| `event: route` | 路线规划结果（含坐标和路径） |
| `event: message` / `type: done` | 对话结束 |

## 知识库说明

知识库位于 `data/raw/` 目录，以 Markdown 格式存储，包含以下内容：

- **江郎山**：门票价格、交通方式、核心景点（三爿石、十八曲古道等）
- **烂柯山**：门票价格、围棋文化、交通路线
- **美食**：烂柯卤水、龙游发糕、常山胡柚、开化清水鱼、烤饼等
- **交通**：市内公交、长途客运、高速路网

知识库分块存储在 `data/processed/chunks.json`，首次启动时自动构建 ChromaDB 向量索引。

## 工作流程

```
用户提问 → 安全过滤
         ↓
    DeepSeek（带 tools）
    ├── 触发 tool_call → 执行工具（天气/路线/POI）→ 喂回结果 → 生成回答
    └── 无 tool_call → RAG 检索（语义 + BM25 → RRF → Reranker）→ 注入上下文 → 生成回答
         ↓
    SSE 流式输出到前端
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

## 开源协议

本项目采用 **MIT 协议** 开源。简单来说：任何人都可以自由使用、修改、分发这份代码，不管是个人学习还是商业用途，只需保留原作者版权声明即可。详情见 [MIT 协议全文](https://mit-license.org/)。