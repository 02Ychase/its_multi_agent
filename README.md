# ITS Multi-Agent 智能客服系统

基于多智能体架构的智能客服系统，支持技术咨询、服务站导航、订单售后、知识库 RAG 检索等场景。

## 系统架构

```
                         ┌──────────────────────┐
                         │    Vue 3 前端界面      │
                         │  (Element Plus UI)    │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │   FastAPI 后端服务     │
                         │   (JWT 认证 + SSE)    │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │     Orchestrator Agent         │
                    │   (意图识别 · 任务编排 · 路由)  │
                    └──┬──────────┬──────────┬──────┘
                       │          │          │
              ┌────────▼──┐ ┌────▼─────┐ ┌──▼──────────┐
              │ Technical  │ │ Service  │ │ After-Sales │
              │  Expert    │ │  Expert  │ │   Expert    │
              └────┬───┬──┘ └──┬───┬──┘ └──┬──────┬──┘
                   │   │       │   │        │      │
              知识库  联网   服务站  地图    订单    保修
              RAG   搜索    查询   导航    查询    查询
```

## 核心功能

### 多智能体协作（Tool Calling + Handoff 双模式）

| Agent | 职责 | 工具 |
|-------|------|------|
| **Orchestrator** | 意图识别、任务编排、结果聚合 | 调度子 Agent |
| **Technical Expert** | 技术故障诊断、实时资讯查询 | 知识库 RAG + WebSearch MCP |
| **Service Expert** | 服务站查询、POI 导航 | 本地服务站库 + 百度地图 MCP |
| **After-Sales Expert** | 订单物流、保修查询、维修进度 | 订单/保修/工单系统 |

- **Tool Calling**：简单任务直接调用子 Agent 工具函数
- **Handoff**：复杂多轮任务将控制权移交给子 Agent

### RAG 检索管线

```
用户问题 → HyDE 查询改写 → BM25 + 向量 + 标题 三路召回 → 去重融合 → Reranker 重排 → Top-K 结果
```

- **HyDE**：生成假设性文档，提升向量检索召回率
- **BM25**：基于 jieba 分词的中文关键词检索
- **向量检索**：DashScope text-embedding-v4 + ChromaDB
- **Reranker**：bge-reranker-v2-m3（可选）

### Langfuse 可观测性

- `@observe` 装饰器追踪 Agent、Tool、Retrieval 调用链路
- LLM-as-Judge 评测框架（13 条测试用例）

### JWT 认证

- 注册 / 登录 / Token 刷新
- bcrypt 密码哈希
- 路由级鉴权守卫

### Docker 一键部署

8 个服务容器化：MySQL、Langfuse DB、Langfuse Server、Backend、Knowledge、Agent Web UI、Knowledge UI、Nginx

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite 5 + Element Plus + vue-router + Pinia |
| 后端 | FastAPI + OpenAI Agents SDK + LangChain |
| 向量库 | ChromaDB |
| 嵌入模型 | DashScope text-embedding-v4 |
| MCP 服务 | DashScope WebSearch + 百度地图 |
| 可观测 | Langfuse |
| 数据库 | MySQL 8.0 |
| 容器化 | Docker Compose + Nginx 反向代理 |

## 项目结构

```
its_multi_agent/
├── backend/
│   ├── app/                              # 主应用服务 (端口 8000)
│   │   ├── api/
│   │   │   ├── main.py                   # FastAPI 入口 + 生命周期
│   │   │   ├── routers.py                # 对话/会话 API
│   │   │   └── auth_router.py            # JWT 认证 API
│   │   ├── multi_agent/                  # 智能体定义
│   │   │   ├── orchestrator_agent.py     # 主调度 Agent
│   │   │   ├── technical_agent.py        # 技术专家 Agent
│   │   │   ├── service_agent.py          # 服务站专家 Agent
│   │   │   ├── after_sales_agent.py      # 订单售后 Agent
│   │   │   └── agent_factory.py          # Agent 工具 + Handoff 注册
│   │   ├── prompts/                      # 系统提示词 (Markdown)
│   │   │   ├── orchestrator_v2.md
│   │   │   ├── technical_agent.md
│   │   │   ├── comprehensive_service_agent.md
│   │   │   └── after_sales_agent.md
│   │   ├── infrastructure/
│   │   │   ├── ai/                       # LLM 客户端 + Prompt 加载器
│   │   │   ├── tools/local/              # 本地工具 (知识库/服务站/售后)
│   │   │   ├── tools/mcp/                # MCP 服务 (搜索/地图)
│   │   │   ├── database/                 # MySQL 连接池
│   │   │   └── observability/            # Langfuse 客户端
│   │   ├── services/                     # 业务服务层
│   │   ├── repositories/                 # 数据仓储层
│   │   ├── models/                       # 数据模型 (用户表)
│   │   ├── schemas/                      # Pydantic 请求/响应模型
│   │   ├── evaluation/                   # LLM-as-Judge 评测框架
│   │   └── prompts/                      # Agent 提示词
│   │
│   └── knowledge/                        # 知识库服务 (端口 8001)
│       ├── api/routers.py                # 上传/查询 API
│       ├── services/
│       │   ├── retrieval_service.py      # RAG 检索管线
│       │   ├── hyde.py                   # HyDE 查询改写
│       │   ├── bm25_retriever.py         # BM25 关键词检索
│       │   └── reranker.py               # bge-reranker 重排
│       └── repositories/
│           └── vector_store_repository.py # ChromaDB 向量存储
│
├── front/
│   ├── agent_web_ui/                     # 智能体对话前端 (端口 5173)
│   │   └── src/
│   │       ├── views/                    # LoginView / ChatView
│   │       ├── components/               # Sidebar / ChatMessage / ChatInput 等
│   │       ├── stores/                   # Pinia (auth / chat)
│   │       └── router/                   # vue-router 路由守卫
│   │
│   └── knowlege_platform_ui/             # 知识库管理前端 (端口 3000)
│       └── src/
│           ├── views/                    # Knowledge / Chat
│           ├── api/                      # Axios 请求封装
│           └── layout/                   # 侧边栏布局
│
├── docker/
│   ├── backend.Dockerfile
│   ├── knowledge.Dockerfile
│   ├── frontend-agent.Dockerfile
│   ├── frontend-knowledge.Dockerfile
│   └── nginx/default.conf
│
├── docker-compose.yml                    # 8 服务一键部署
├── start_all.bat                         # Windows 一键启动
└── stop.bat                              # Windows 一键停止
```

## 快速开始

### 方式一：本地开发

```bash
# 1. 克隆仓库
git clone <repository_url>
cd its_multi_agent

# 2. 安装后端依赖
cd backend/app
pip install -r requirements.txt

# 3. 配置环境变量
# 编辑 backend/app/.env 和 backend/knowledge/.env

# 4. 启动后端服务
cd backend/app
python api/main.py                        # 主服务 :8000

# 5. 启动知识库服务
cd backend/knowledge
uvicorn api.main:app --port 8001          # 知识库服务 :8001

# 6. 启动前端
cd front/agent_web_ui && npm run dev      # 对话界面 :5173
cd front/knowlege_platform_ui && npm run dev  # 知识库管理 :3000
```

### 方式二：Docker 一键部署

```bash
# 配置环境变量后
docker-compose up -d

# 访问
# 对话界面:   http://localhost
# Langfuse:   http://localhost:3001
```

### 方式三：Windows 脚本

```bash
start_all.bat    # 后台启动所有服务
stop.bat         # 停止所有服务
```

## 环境变量

### 主应用 (`backend/app/.env`)

```bash
# LLM
API_KEY=your_api_key
BASE_URL=https://api.siliconflow.cn/v1
MODEL=Qwen/Qwen3-32B

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=its_db

# Langfuse (可选)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=http://localhost:3001

# JWT
JWT_SECRET_KEY=change-me-in-production

# MCP
DASHSCOPE_API_KEY=your_dashscope_key
BAIDUMAP_AK=your_baidu_map_ak
```

### 知识库服务 (`backend/knowledge/.env`)

```bash
# LLM (与主 Agent 一致)
API_KEY=your_api_key
BASE_URL=https://api.siliconflow.cn/v1
MODEL=Qwen/Qwen3-32B

# 嵌入模型 (DashScope)
EMBEDDING_API_KEY=your_dashscope_key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
```

## API 接口

### 对话（SSE 流式）

```http
POST /api/query
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "电脑蓝屏怎么办",
  "context": { "user_id": "user1", "session_id": "session_123" }
}
```

### 认证

```http
POST /api/auth/register    # 注册
POST /api/auth/login       # 登录
POST /api/auth/refresh     # 刷新 Token
```

### 知识库

```http
POST /api/upload           # 上传文档 (multipart/form-data)
POST /api/query            # 知识库问答
```

## 使用示例

```
用户：电脑开机蓝屏代码0x0000007B怎么解决？
→ Orchestrator → Technical Expert → 知识库 RAG 检索 → 返回解决方案

用户：帮我找最近的联想服务站
→ Orchestrator → Service Expert → 服务站查询 + 百度地图 → 返回地址 + 导航链接

用户：订单号 ORD20240512001 到哪了？
→ Orchestrator → After-Sales Expert → 订单查询 → 返回物流状态

用户：查一下今天北京天气，然后帮我找最近的维修站
→ Orchestrator → Technical Expert (天气) + Service Expert (服务站) → 聚合结果
```

## License

本项目仅供学习研究使用。
