# ITS Multi-Agent 智能客服系统

基于多智能体架构的企业级智能客服系统，支持技术咨询、服务站导航、订单售后和知识库 RAG 检索。采用 OpenAI Agents SDK 构建 Agent-as-Tool 调度体系，配合输入/输出护栏、上下文压缩、查询路由等企业级能力。

## 系统架构

```
                          ┌────────────────────────────┐
                          │      Vue 3 前端界面          │
                          │  (Element Plus · Pinia)     │
                          └────────────┬───────────────┘
                                       │ SSE / JWT
                          ┌────────────▼───────────────┐
                          │    FastAPI 主后端 (:8000)     │
                          │ 护栏 · 限流 · 反馈 · 健康检查  │
                          └────────────┬───────────────┘
                                       │
                     ┌─────────────────▼─────────────────┐
                     │      Orchestrator Agent (主模型)     │
                     │    意图识别 · 任务编排 · 结果聚合      │
                     │  输入护栏 ← ─ ─ ─ ─ → 输出护栏       │
                     └──┬──────────┬───────────┬─────────┘
                        │          │           │
               ┌────────▼──┐ ┌────▼─────┐ ┌───▼──────────┐
               │ Technical  │ │ Service  │ │  After-Sales  │
               │  Expert    │ │  Expert  │ │   Expert      │
               └──┬─────┬──┘ └──┬────┬──┘ └──┬────────┬──┘
                  │     │       │    │        │        │
             知识库   联网    服务站  地图    订单     保修
             RAG    搜索    MySQL  MCP    MySQL    MySQL
               │
    ┌──────────▼───────────┐
    │ Knowledge Service     │
    │     (:8001)           │
    │ 查询路由 · 语义分块     │
    │ BM25持久化 · HyDE      │
    └───────────────────────┘
```

## 核心功能

### 多智能体协作（Agent-as-Tool 模式）

| Agent | 职责 | 工具 | 模型 |
|-------|------|------|------|
| **Orchestrator** | 意图识别、任务编排、结果聚合 | 调度三个子 Agent | 主模型 |
| **Technical Expert** | 技术故障诊断、实时资讯查询 | 知识库 RAG + DashScope WebSearch MCP | 子模型 |
| **Service Expert** | 服务站查询、POI 导航 | MySQL 服务站库 + 百度地图 MCP | 子模型 |
| **After-Sales Expert** | 订单物流、保修查询、维修进度 | MySQL 订单/保修/工单表 | 子模型 |

子 Agent 通过 `@function_tool` 包装为工具函数，由 Orchestrator 经 `Runner.run()` 调度。

### RAG 检索管线

```
用户问题
   │
   ▼
查询路由 ──→ SIMPLE:  跳过 HyDE，直接三路检索
(规则分类)    STANDARD: HyDE 改写 + 三路检索（默认）
              COMPLEX: 分解子查询，分别检索后合并
   │
   ▼
三路并行召回
  ├── BM25 关键词检索（jieba 分词，持久化索引）
  ├── 向量相似度检索（DashScope text-embedding-v4 + ChromaDB）
  └── 标题匹配检索（粗排 + 精排两阶段）
   │
   ▼
去重融合 → bge-reranker-v2-m3 重排 → Top-K 结果
```

### 安全与治理

- **输入护栏**：Prompt Injection 正则检测、输入长度限制（2000 字）、敏感关键词过滤
- **输出护栏**：PII 模式检测（手机号、身份证、银行卡等）
- **频率限制**：`/api/query` 接口 10 次/分钟（slowapi）
- **JWT 认证**：bcrypt 密码哈希 + HS256 签名，Access Token 30 分钟 + Refresh Token 7 天
- **启动安全检查**：检测默认 JWT 密钥并输出 WARNING 日志

### 可观测性

- **Langfuse 全链路追踪**：`@observe` 装饰器覆盖 Agent、Tool、Retrieval 调用链
- **健康检查**：主后端 `/health`（MySQL + MCP）、知识库 `/health`（ChromaDB）
- **用户反馈**：`/api/feedback` 端点收集有用/无用评价
- **工具调用统计**：`/api/tool_calls/summary` 查询各工具调用次数

### 上下文管理

- **LLM 上下文压缩**：超出滑动窗口的历史对话由 LLM 压缩为摘要，降低 Token 消耗
- **会话持久化**：MySQL 存储会话和消息，支持多设备同步

### 知识库增强

- **语义分块**：Markdown 文件按标题层级（h1/h2/h3）语义切分，超长块二级字符切分
- **BM25 持久化**：pickle 序列化索引 + 目录 hash 自动失效，避免重启重建
- **文档上传后自动重建 BM25 索引**

### SSE 流式响应

四种内容类型：

| Kind | 说明 | 前端渲染 |
|------|------|---------|
| `ANSWER` | 最终回答 | 主聊天气泡 |
| `THINKING` | 思考/推理 | 可折叠区域 |
| `PROCESS` | 工具调用/系统流程 | 可折叠区域 |
| `STRUCTURED` | 结构化数据（订单/保修/维修卡片） | 数据卡片 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite 5 + Element Plus + Pinia + vue-router |
| 后端框架 | FastAPI + SSE 流式响应 + slowapi 限流 |
| Agent SDK | OpenAI Agents SDK（Agent-as-Tool 模式） |
| RAG 框架 | LangChain + ChromaDB + bge-reranker-v2-m3 |
| 嵌入模型 | DashScope text-embedding-v4 |
| MCP 服务 | DashScope WebSearch (StreamableHTTP) + 百度地图 (SSE) |
| 可观测 | Langfuse（全链路追踪 + 评测） |
| 数据库 | MySQL 8.0（用户/会话/消息/售后/反馈） |
| 认证 | JWT (bcrypt + HS256) + Token 自动刷新 |
| 容器化 | Docker Compose（8 服务）+ Nginx 反向代理 |
| 代码质量 | Ruff (lint) + pytest + GitHub Actions CI |

## 项目结构

```
its_multi_agent/
├── backend/
│   ├── app/                                  # 主应用服务 (:8000)
│   │   ├── api/
│   │   │   ├── main.py                       # FastAPI 入口 + 生命周期管理
│   │   │   ├── routers.py                    # 对话/会话/反馈/健康检查 API
│   │   │   └── auth_router.py                # JWT 认证 API
│   │   ├── multi_agent/                      # 智能体定义
│   │   │   ├── orchestrator_agent.py         # 主调度 Agent（主模型 + 护栏）
│   │   │   ├── technical_agent.py            # 技术专家 Agent
│   │   │   ├── service_agent.py              # 服务站专家 Agent
│   │   │   ├── after_sales_agent.py          # 订单售后 Agent
│   │   │   ├── agent_factory.py              # Agent → @function_tool 注册
│   │   │   └── guardrails.py                 # 输入/输出安全护栏
│   │   ├── services/
│   │   │   ├── agent_service.py              # 多智能体任务入口
│   │   │   ├── stream_response_service.py    # SSE 事件流处理
│   │   │   ├── conversation_service.py       # 会话管理 + 历史构建
│   │   │   ├── context_compressor.py         # LLM 上下文压缩
│   │   │   ├── auth_service.py               # 认证服务
│   │   │   └── tool_execution_service.py     # 工具执行治理
│   │   ├── infrastructure/
│   │   │   ├── ai/                           # LLM 客户端 + Prompt 加载器
│   │   │   ├── tools/local/                  # 本地工具（知识库/服务站/售后）
│   │   │   ├── tools/mcp/                    # MCP 客户端（搜索/地图）
│   │   │   ├── database/                     # MySQL 连接池 (DBUtils)
│   │   │   ├── observability/                # Langfuse 客户端
│   │   │   └── rate_limiter.py               # slowapi 限流器
│   │   ├── repositories/                     # 数据仓储层
│   │   │   ├── after_sales_repository.py     # 售后三表（订单/保修/工单）
│   │   │   ├── feedback_repository.py        # 用户反馈表
│   │   │   ├── chat_session_repository.py    # 会话表
│   │   │   └── chat_message_repository.py    # 消息表
│   │   ├── schemas/                          # Pydantic 请求/响应模型
│   │   ├── prompts/                          # Agent 提示词 (Markdown)
│   │   ├── evaluation/                       # LLM-as-Judge 评测框架
│   │   ├── scripts/                          # 数据初始化脚本
│   │   └── tests/                            # 单元测试
│   │
│   └── knowledge/                            # 知识库服务 (:8001)
│       ├── api/routers.py                    # 上传/查询/文档管理/健康检查 API
│       ├── services/
│       │   ├── retrieval_service.py          # RAG 检索管线（查询路由集成）
│       │   ├── query_router.py               # 查询复杂度分类器
│       │   ├── ingestion/
│       │   │   └── ingestion_processor.py    # 文档摄入（语义分块 + 字符分块）
│       │   ├── bm25_retriever.py             # BM25 检索（持久化索引）
│       │   ├── hyde.py                       # HyDE 查询改写
│       │   ├── reranker.py                   # bge-reranker 重排
│       │   └── crawler/                      # 网页爬虫
│       ├── repositories/
│       │   └── vector_store_repository.py    # ChromaDB 向量存储
│       └── tests/                            # 单元测试
│
├── front/
│   ├── agent_web_ui/                         # 智能体对话前端 (:5173)
│   │   └── src/
│   │       ├── views/                        # LoginView / ChatView
│   │       ├── components/                   # ChatMessage / ChatInput / Sidebar 等
│   │       ├── stores/                       # Pinia (auth + chat，含 token 自动刷新)
│   │       └── router/                       # vue-router 路由守卫
│   │
│   └── knowlege_platform_ui/                 # 知识库管理前端 (:3000)
│       └── src/
│           ├── views/                        # 文档上传 / 知识问答
│           └── api/                          # Axios 请求封装
│
├── docker/                                   # Dockerfile + Nginx 配置
├── docker-compose.yml                        # 8 服务一键部署
├── pyproject.toml                            # Ruff + pytest 配置
├── .github/workflows/ci.yml                  # CI 流水线
├── start_all.bat                             # Windows 一键启动
└── stop.bat                                  # Windows 一键停止
```

## 快速开始

### 前置条件

- Python 3.10+
- Node.js 18+
- MySQL 8.0
- LLM API Key（主模型 + 子模型）
- DashScope API Key（嵌入模型 + WebSearch）
- 百度地图 AK

### 方式一：本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/02Ychase/its_multi_agent.git
cd its_multi_agent

# 2. 安装后端依赖
cd backend/app && pip install -r requirements.txt
cd ../knowledge && pip install -r requirements.txt

# 3. 配置环境变量（参见下方环境变量章节）
# 编辑 backend/app/.env 和 backend/knowledge/.env

# 4. 启动主后端（自动建表）
cd backend/app
python api/main.py                          # :8000

# 5. 初始化售后示例数据（首次）
python scripts/init_after_sales_data.py

# 6. 启动知识库服务
cd backend/knowledge
uvicorn api.main:app --port 8001            # :8001

# 7. 启动前端
cd front/agent_web_ui && npm install && npm run dev       # :5173
cd front/knowlege_platform_ui && npm install && npm run dev  # :3000
```

### 方式二：Docker 一键部署

```bash
# 配置 backend/app/.env 和 backend/knowledge/.env 后
docker compose up -d

# 访问
# 对话界面:   http://localhost
# Langfuse:   http://localhost:3001
```

### 方式三：Windows 脚本

```bash
start_all.bat    # 后台启动 Backend(:8000) + Knowledge(:8001) + 两个前端
stop.bat         # 停止所有服务
```

## 环境变量

### 主应用 (`backend/app/.env`)

```bash
# ===== LLM 主模型（Orchestrator 使用）=====
MAIN_API_KEY=your_main_api_key
MAIN_BASE_URL=https://api.example.com/v1
MAIN_MODEL_NAME=MiMo-V2.5-Pro

# ===== LLM 子模型（子 Agent 使用）=====
SUB_API_KEY=your_sub_api_key
SUB_BASE_URL=https://api.example.com/v1
SUB_MODEL_NAME=MiniMax-m2.7

# ===== MySQL =====
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=its_db

# ===== JWT（生产环境必须修改）=====
JWT_SECRET_KEY=change-me-in-production

# ===== MCP 外部服务 =====
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=your_dashscope_key
BAIDUMAP_AK=your_baidu_map_ak

# ===== Langfuse（可选）=====
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=http://localhost:3001

# ===== CORS =====
CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 知识库服务 (`backend/knowledge/.env`)

```bash
# ===== LLM =====
API_KEY=your_api_key
BASE_URL=https://api.example.com/v1
MODEL=MiMo-V2.5-Pro

# ===== 嵌入模型 (DashScope) =====
EMBEDDING_API_KEY=your_dashscope_key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4

# ===== 可选配置 =====
HYDE_ENABLED=true
RERANKER_ENABLED=true
```

### 前端 (`front/agent_web_ui/.env`)

```bash
VITE_API_BASE=http://127.0.0.1:8000
```

## API 接口

### 对话（SSE 流式）

```http
POST /api/query
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "query": "电脑蓝屏怎么办",
  "context": { "user_id": "user1", "session_id": "session_123" }
}
```

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录（返回 access + refresh token） |
| POST | `/api/auth/refresh` | 刷新 Access Token |
| POST | `/api/auth/logout` | 登出（吊销 Refresh Token） |
| GET | `/api/auth/me` | 获取当前用户信息 |

### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/user_sessions` | 获取用户所有会话 |
| POST | `/api/delete_session` | 删除指定会话 |

### 反馈与监控

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/feedback` | 提交回答反馈（有用/无用） |
| GET | `/api/tool_calls/summary` | 工具调用统计 |
| GET | `/health` | 健康检查（MySQL + MCP） |

### 知识库

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/upload` | 上传文档（.md / .txt / .pdf / .docx） |
| POST | `/query` | 知识库问答 |
| POST | `/retrieval` | 检索原始上下文（评测用） |
| GET | `/documents` | 文档列表（分页 + 状态过滤） |
| DELETE | `/documents/{id}` | 删除文档 |
| POST | `/documents/{id}/reindex` | 重建文档索引 |
| GET | `/health` | 健康检查（ChromaDB） |

## 使用示例

```
用户：电脑开机蓝屏代码 0x0000007B 怎么解决？
  → Orchestrator → Technical Expert → 知识库 RAG 检索 → 返回解决方案

用户：帮我找最近的联想服务站
  → Orchestrator → Service Expert → MySQL 服务站查询 + 百度地图导航 → 返回地址和路线

用户：订单号 ORD20240512001 到哪了？
  → Orchestrator → After-Sales Expert → MySQL 订单查询 → 返回物流状态卡片

用户：我的笔记本保修期到什么时候？
  → Orchestrator → After-Sales Expert → MySQL 保修查询 → 返回保修信息卡片
```

## CI/CD

项目使用 GitHub Actions 进行持续集成：

```yaml
# .github/workflows/ci.yml
Jobs:
  - backend-app:       Ruff lint + pytest（主后端）
  - backend-knowledge: Ruff lint + pytest（知识库）
  - frontend:          npm build（两个前端）
  - docker-config:     docker compose config（配置验证）
```

## 数据库表结构

应用启动时自动创建以下表（无需手动建表）：

| 表名 | 说明 |
|------|------|
| `users` | 用户账号（bcrypt 密码哈希） |
| `refresh_tokens` | JWT Refresh Token 管理 |
| `chat_sessions` | 会话记录 |
| `chat_messages` | 消息记录 |
| `agent_events` | Agent 事件日志 |
| `orders` | 订单信息 |
| `warranty_records` | 保修记录 |
| `repair_tickets` | 维修工单 |
| `tool_call_logs` | 工具调用日志 |
| `user_feedback` | 用户反馈 |

## License

本项目仅供学习研究使用。
