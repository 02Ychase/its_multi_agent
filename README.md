# ITS Multi-Agent System

## 项目概述

ITS Multi-Agent System 是一个基于多智能体架构的智能客服系统，主要服务于电脑技术支持和服务中心导航场景。系统采用主从式多智能体设计，能够根据用户意图自动调度专业智能体处理不同类型的任务，包括技术咨询、服务站查询、导航等。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        ITS Multi-Agent System                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐                                              │
│  │   Orchestrator Agent (主调度智能体)                          │
│  │   - 意图识别与任务分发                                         │
│  │   - 多智能体协调                                              │
│  └──────┬──────┘                                              │
│         │                                                       │
│    ┌────┴────┬─────────────┐                                   │
│    │         │             │                                    │
│ ┌──▼──┐   ┌─▼────┐    ┌───▼────┐                               │
│ │技术  │   │服务站 │    │全能业务  │                               │
│ │智能体 │   │智能体 │    │智能体   │                               │
│ └─────┘   └──────┘    └────────┘                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                           前端界面                                │
│  ├─ agent_web_ui: 智能体对话界面                                 │
│  └─ knowlege_platform_ui: 知识库管理平台                        │
├─────────────────────────────────────────────────────────────────┤
│                           后端服务                                │
│  ├─ app/: 主应用服务 (多智能体编排)                               │
│  ├─ knowledge/: 知识库服务 (RAG检索)                            │
│  └─ openai-agents-tutorial/: OpenAI Agents教程                   │
└─────────────────────────────────────────────────────────────────┘
```

## 智能体说明

| 智能体 | 名称 | 职责 | 可调用的工具 |
|--------|------|------|--------------|
| orchestrator_agent | 主调度智能体 | 理解用户意图、拆解任务、调度子智能体 | `consult_technical_expert`, `query_service_station_and_navigate` |
| technical_agent | 技术专家智能体 | 处理技术咨询、故障诊断、实时资讯查询 | `query_knowledge` (本地知识库) + Search MCP |
| service_agent | 全能业务智能体 | 处理服务站查询、POI导航、路线规划 | `resolve_user_location_from_text`, `query_nearest_repair_shops_by_coords` + 百度地图MCP |

## 技术栈

### 后端
- **框架**：FastAPI + Uvicorn
- **智能体框架**：OpenAI Agents SDK (`openai-agents`)
- **配置管理**：Pydantic Settings
- **数据库**：MySQL (使用DBUtils连接池)
- **HTTP客户端**：httpx
- **环境管理**：python-dotenv

### 前端
- **框架**：Vue 3 + Vite 5
- **UI组件库**：Element Plus
- **Markdown渲染**：marked
- **HTTP客户端**：axios

### MCP 服务
- **通义千问搜索**：WebSearch MCP Server
- **百度地图**：Baidu Map MCP Server

## 项目结构

```
its_multi_agent/
├── backend/
│   ├── app/                          # 主应用服务
│   │   ├── api/
│   │   │   ├── main.py              # FastAPI入口
│   │   │   └── routers.py           # API路由定义
│   │   ├── config/
│   │   │   └── settings.py          # 应用配置
│   │   ├── infrastructure/
│   │   │   ├── ai/                  # AI基础设施
│   │   │   │   ├── openai_client.py # OpenAI客户端配置
│   │   │   │   └── prompt_loader.py # Prompt加载器
│   │   │   ├── database/            # 数据库连接池
│   │   │   ├── logging/             # 日志模块
│   │   │   └── tools/               # 工具定义
│   │   │       ├── local/           # 本地工具
│   │   │       │   ├── knowledge_base.py
│   │   │       │   └── service_station.py
│   │   │       └── mcp/             # MCP工具
│   │   │           ├── mcp_manager.py
│   │   │           └── mcp_servers.py
│   │   ├── multi_agent/             # 智能体定义
│   │   │   ├── orchestrator_agent.py # 主调度智能体
│   │   │   ├── technical_agent.py   # 技术专家智能体
│   │   │   ├── service_agent.py     # 全能业务智能体
│   │   │   ├── agent_factory.py     # Agent工厂
│   │   │   └── ...
│   │   ├── prompts/                 # 系统Prompts
│   │   ├── repositories/            # 数据仓库
│   │   ├── schemas/                 # Pydantic模型
│   │   ├── services/                # 业务服务层
│   │   ├── tests/                   # 测试代码
│   │   ├── .env                     # 环境配置
│   │   └── requirements.txt         # 依赖清单
│   │
│   ├── knowledge/                   # 知识库服务
│   │   └── ...
│   │
│   └── openai-agents-tutorial/      # OpenAI Agents教程
│
└── front/                           # 前端应用
    ├── agent_web_ui/                # 智能体对话UI
    │   ├── package.json
    │   └── ...
    │
    └── knowlege_platform_ui/        # 知识库管理UI
        ├── package.json
        └── ...
```

## 核心功能

### 1. 多智能体协同
- **意图识别**：主调度智能体自动识别用户意图，区分技术问题、服务站查询、导航等
- **任务分发**：根据意图将任务分发给对应的子智能体
- **多步任务处理**：支持多步任务（如"查天气，然后导航去服务站"）
- **流式响应**：完整的流式输出，包括思考过程、工具调用、最终结果

### 2. 技术咨询
- **知识库检索**：通过RAG技术检索内部知识库
- **网络搜索**：使用通义千问搜索MCP获取实时资讯
- **故障诊断**：提供电脑故障诊断和解决方案

### 3. 服务站与导航
- **服务站查询**：查询最近的服务站、官方维修点
- **POI搜索**：搜索公共场所（商场、医院等）
- **路线规划**：生成导航链接和路线规划

## 配置说明

### 后端环境变量 (`backend/app/.env`)

```bash
# AI 服务配置 (支持硅基流动和阿里百炼)
SF_API_KEY=your_siliconflow_api_key
SF_BASE_URL=https://api.siliconflow.cn/v1
MAIN_MODEL_NAME=Qwen/Qwen3-32B

AL_BAILIAN_API_KEY=your_alibailian_api_key
AL_BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
SUB_MODEL_NAME=qwen3-max

# MySQL 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=its

# MCP 服务配置
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/sse
BAIDUMAP_AK=your_baidu_map_ak

# 知识库服务地址
KNOWLEDGE_BASE_URL=http://127.0.0.1:8001
```

## API 接口

### 对话接口

```http
POST /api/query
Content-Type: application/json

{
  "query": "电脑开机蓝屏怎么办",
  "context": {
    "user_id": "user123",
    "session_id": "session456"
  },
  "flag": true
}
```

**响应格式**：SSE (Server-Sent Events) 流式响应

### 获取用户会话列表

```http
POST /api/user_sessions
Content-Type: application/json

{
  "user_id": "user123"
}
```

## 快速开始

### 1. 克隆仓库

```bash
git clone <repository_url>
cd its_multi_agent
```

### 2. 配置环境变量

复制示例环境变量文件并修改：

```bash
# 主应用服务
cp backend/app/.env.example backend/app/.env
# 编辑 backend/app/.env 填写API密钥和数据库配置
```

### 3. 安装后端依赖

```bash
cd backend/app
pip install -r requirements.txt
```

### 4. 安装前端依赖

```bash
# 知识库管理UI
cd front/knowlege_platform_ui
npm install

# 智能体对话UI
cd front/agent_web_ui
npm install
```

### 5. 启动服务

```bash
# 启动主应用服务 (智能体编排)
cd backend/app
python api/main.py
# 服务启动在 http://127.0.0.1:8000

# 启动知识库服务 (如需要本地知识库)
cd backend/knowledge
# 启动知识库服务

# 启动知识库管理前端
cd front/knowlege_platform_ui
npm run dev

# 启动智能体对话前端
cd front/agent_web_ui
npm run dev
```

## 使用示例

### 示例1：技术咨询

```
用户：电脑开机蓝屏代码0x0000007B怎么解决？

智能体：调用 technical_agent
→ 检索知识库 + 搜索网络
→ 返回：蓝屏代码含义及解决方案
```

### 示例2：服务站查询

```
用户：帮我找最近的联想服务站

智能体：调用 service_agent
→ 解析用户位置 + 查询服务站数据库 + 调用百度地图
→ 返回：最近服务站地址、电话、导航链接
```

### 示例3：多步任务

```
用户：查一下今天北京的天气，如果下雨的话帮我找最近的服务站

智能体：
→ step1: 调用 technical_agent 获取天气
→ step2: 调用 service_agent 查询服务站
→ 聚合结果返回
```

## 开发团队

- 架构设计：基于 OpenAI Agents 框架
- 前端：Vue 3 + Element Plus
- 后端：FastAPI + Python

## License

本项目仅供学习研究使用。