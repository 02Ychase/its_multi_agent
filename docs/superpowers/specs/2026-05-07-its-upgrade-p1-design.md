# ITS Multi-Agent System P1 Upgrade Design

## Overview

Upgrade the ITS Multi-Agent system with three P1 priorities:
1. Docker full containerization (all services in one compose)
2. JWT authentication (FastAPI OAuth2 + JWT + user registration)
3. Agent Handoff upgrade (dual mode: Tool Calling + Handoff)

**Implementation order**: Docker first (infrastructure) → JWT (security) → Handoff (architecture).

## Tech Stack

- **Containerization**: Docker + Docker Compose + Nginx reverse proxy
- **Auth**: FastAPI OAuth2 + passlib[bcrypt] + python-jose[HS256]
- **Agent**: openai-agents SDK (Handoff support)
- **Database**: MySQL 8.0 (users table + existing repair shops)
- **Frontend**: Vue 3 + Element Plus (login/Token handling)

---

## Phase 1: Docker Full Containerization

### 1.1 Service Architecture

```
Nginx (port 80)
├── /              → Agent Web UI (Vue SPA, built)
├── /knowledge     → Knowledge Platform UI (Vue SPA, built)
├── /api/*         → Backend API (FastAPI :8000)
└── /knowledge-api/* → Knowledge Service (FastAPI :8001)

Docker Network (bridge: its-network)
├── mysql          (mysql:8.0, port 3306)
├── backend        (python:3.10-slim, port 8000)
├── knowledge      (python:3.10-slim, port 8001)
├── agent-web-ui   (nginx:alpine)
├── knowledge-ui   (nginx:alpine)
├── nginx-proxy    (nginx:alpine, port 80)
├── langfuse-server (langfuse/langfuse:latest, port 3001)
└── langfuse-db    (postgres:15-alpine)
```

### 1.2 Dockerfiles

**docker/backend.Dockerfile**
- Base: python:3.10-slim
- Install dependencies from requirements.txt
- Copy backend/app source
- CMD: uvicorn api.main:create_fast_api --host 0.0.0.0 --port 8000

**docker/knowledge.Dockerfile**
- Base: python:3.10-slim
- Install dependencies from requirements.txt (including rank_bm25, FlagEmbedding)
- Copy backend/knowledge source + data/crawl + chroma_kb1
- CMD: uvicorn api.main:create_fast_api --host 0.0.0.0 --port 8001

**docker/frontend-agent.Dockerfile**
- Multi-stage: node:18-alpine (build) → nginx:alpine (serve)
- npm run build, copy dist to nginx html

**docker/frontend-knowledge.Dockerfile**
- Multi-stage: node:18-alpine (build) → nginx:alpine (serve)
- npm run build, copy dist to nginx html

### 1.3 Nginx Configuration

**docker/nginx/nginx.conf**: Main config with upstream definitions
**docker/nginx/default.conf**: Server blocks with reverse proxy rules

```nginx
server {
    listen 80;

    # Agent Web UI (Vue SPA)
    location / {
        proxy_pass http://agent-web-ui:80;
        try_files $uri $uri/ /index.html;
    }

    # Knowledge Platform UI (Vue SPA)
    location /knowledge {
        proxy_pass http://knowledge-ui:80;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend:8000;
    }

    # Knowledge Service API
    location /knowledge-api/ {
        proxy_pass http://knowledge:8001/;
    }
}
```

### 1.4 docker-compose.yml

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
    volumes:
      - mysql-data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s

  langfuse-db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: langfuse
      POSTGRES_PASSWORD: langfuse_secret
      POSTGRES_DB: langfuse
    volumes:
      - langfuse-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse"]

  langfuse-server:
    image: langfuse/langfuse:latest
    ports:
      - "3001:3000"
    environment:
      DATABASE_URL: postgresql://langfuse:langfuse_secret@langfuse-db:5432/langfuse
    depends_on:
      langfuse-db: { condition: service_healthy }

  backend:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    ports:
      - "8000:8000"
    env_file: backend/app/.env
    environment:
      MYSQL_HOST: mysql
      KNOWLEDGE_BASE_URL: http://knowledge:8001
    depends_on:
      mysql: { condition: service_healthy }
      knowledge: { condition: service_started }

  knowledge:
    build:
      context: .
      dockerfile: docker/knowledge.Dockerfile
    ports:
      - "8001:8001"
    env_file: backend/knowledge/.env
    environment:
      MYSQL_HOST: mysql
    volumes:
      - chroma-data:/app/chroma_kb1
    depends_on:
      mysql: { condition: service_healthy }

  agent-web-ui:
    build:
      context: .
      dockerfile: docker/frontend-agent.Dockerfile

  knowledge-ui:
    build:
      context: .
      dockerfile: docker/frontend-knowledge.Dockerfile

  nginx-proxy:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - backend
      - knowledge
      - agent-web-ui
      - knowledge-ui

volumes:
  mysql-data:
  langfuse-db-data:
  chroma-data:
```

### 1.5 Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `docker-compose.yml` | Main compose file |
| Create | `docker/backend.Dockerfile` | Backend image |
| Create | `docker/knowledge.Dockerfile` | Knowledge service image |
| Create | `docker/frontend-agent.Dockerfile` | Agent UI image |
| Create | `docker/frontend-knowledge.Dockerfile` | Knowledge UI image |
| Create | `docker/nginx/nginx.conf` | Nginx main config |
| Create | `docker/nginx/default.conf` | Nginx site config |
| Modify | `docker/langfuse/docker-compose.yml` | Merge into main compose |
| Create | `.env.docker` | Docker-specific env template |

---

## Phase 2: JWT Authentication

### 2.1 Database Schema

New table `users` in MySQL:

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 2.2 API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | None | Register new user |
| `/api/auth/login` | POST | None | Login, returns tokens |
| `/api/auth/refresh` | POST | refresh_token | Refresh access_token |
| `/api/auth/me` | GET | access_token | Get current user info |
| `/api/query` | POST | access_token | Agent chat (existing) |
| `/api/user_sessions` | POST | access_token | Session list (existing) |

### 2.3 Token Design

- **access_token**: 30 min expiry, payload: `{user_id, username, exp}`
- **refresh_token**: 7 day expiry, payload: `{user_id, type: "refresh", exp}`
- **Algorithm**: HS256, secret from `JWT_SECRET_KEY` env var
- **Header**: `Authorization: Bearer <access_token>`

### 2.4 Security

- Passwords hashed with `passlib[bcrypt]`
- All `/api/*` routes except `/api/auth/*` require valid access_token
- Frontend stores tokens in localStorage
- Frontend adds `Authorization` header to all API requests
- Frontend route guard redirects to login if no valid token

### 2.5 New Dependencies

```
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
```

### 2.6 Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `backend/app/models/__init__.py` | Models package |
| Create | `backend/app/models/user.py` | User SQLAlchemy model |
| Create | `backend/app/services/auth_service.py` | Auth business logic |
| Create | `backend/app/api/auth_router.py` | Auth API routes |
| Modify | `backend/app/api/main.py` | Register auth router |
| Modify | `backend/app/api/routers.py` | Add auth dependency |
| Modify | `backend/app/config/settings.py` | Add JWT settings |
| Modify | `backend/app/requirements.txt` | Add auth deps |
| Modify | `front/agent_web_ui/src/App.vue` | Login/Token logic |

### 2.7 Settings to Add

```python
# JWT Configuration
JWT_SECRET_KEY: str = Field(default="change-me-in-production", description="JWT signing secret")
JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiry")
JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiry")
```

---

## Phase 3: Agent Handoff Upgrade

### 3.1 Dual Mode Architecture

```
User → Orchestrator Agent
         │
         ├─ Simple task → Tool Calling (existing)
         │    └─ call sub-agent as tool → get result → return to user
         │
         └─ Complex task → Handoff (new)
              └─ handoff to sub-agent
                   └─ sub-agent takes over conversation
                        └─ multi-turn interaction
                             └─ handoff back to orchestrator
                                  └─ orchestrator summarizes → return to user
```

### 3.2 Handoff Decision Rules

| Condition | Mode | Example |
|-----------|------|---------|
| Single-turn Q&A, clear intent | Tool Calling | "What's the weather today?" |
| Multi-turn troubleshooting | Handoff | "My PC won't start" → step-by-step diagnosis |
| Multiple tools needed by sub-agent | Handoff | "Find nearest shop and navigate" |
| User needs clarification | Handoff | Ambiguous request requiring follow-up |

### 3.3 openai-agents SDK Handoff

```python
from agents import Agent, handoff

orchestrator_agent = Agent(
    name="主调度智能体",
    instructions=load_prompt("orchestrator_v2"),
    model=sub_model,
    tools=AGENT_TOOLS,  # Tool Calling
    handoffs=[
        handoff(technical_agent),  # Handoff to technical
        handoff(comprehensive_service_agent),  # Handoff to service
    ],
)
```

### 3.4 Orchestrator v2 Prompt Changes

Add to orchestrator_v1.md (create as v2):

```markdown
## Handoff 决策规则

### 使用 Tool Calling（默认）
- 用户问题明确，单轮即可回答
- 信息查询类（天气、股价、知识库）
- 简单的服务站查询或 POI 导航

### 使用 Handoff
- 故障排查需多轮交互（"开不了机"→"检查电源"→"还是不行"）
- 用户需求不明确，需子 Agent 追问
- 复杂多步骤任务，需子 Agent 持续跟进

### 原则
- 默认 Tool Calling，仅明确需多轮时用 Handoff
- Handoff 后等待子 Agent 返回结果
```

### 3.5 Stream Response Handling

Update `stream_response_service.py` to handle handoff events:

```python
# Handle handoff events
elif event.type == "agent_updated_stream_event":
    new_agent_name = event.new_agent.name
    text = format_agent_update_html(new_agent_name)
    yield "data: " + ResponseFactory.build_text(text, ContentKind.PROCESS).model_dump_json() + "\n\n"
```

This already exists in the current code — no change needed for basic handoff support.

### 3.6 Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `backend/app/prompts/orchestrator_v2.md` | New orchestrator prompt with Handoff rules |
| Modify | `backend/app/multi_agent/orchestrator_agent.py` | Add handoffs parameter |
| Modify | `backend/app/multi_agent/agent_factory.py` | Import handoff, adjust exports |

---

## File Change Summary

### New Files (12)
| File | Purpose |
|------|---------|
| `docker-compose.yml` | Main Docker Compose |
| `docker/backend.Dockerfile` | Backend image |
| `docker/knowledge.Dockerfile` | Knowledge service image |
| `docker/frontend-agent.Dockerfile` | Agent UI image |
| `docker/frontend-knowledge.Dockerfile` | Knowledge UI image |
| `docker/nginx/nginx.conf` | Nginx main config |
| `docker/nginx/default.conf` | Nginx site config |
| `backend/app/models/__init__.py` | Models package |
| `backend/app/models/user.py` | User model |
| `backend/app/services/auth_service.py` | Auth service |
| `backend/app/api/auth_router.py` | Auth routes |
| `backend/app/prompts/orchestrator_v2.md` | Handoff orchestrator prompt |

### Modified Files (7)
| File | Change |
|------|--------|
| `backend/app/config/settings.py` | Add JWT settings |
| `backend/app/requirements.txt` | Add auth dependencies |
| `backend/app/api/main.py` | Register auth router |
| `backend/app/api/routers.py` | Add auth dependency |
| `backend/app/multi_agent/orchestrator_agent.py` | Add handoffs |
| `backend/app/multi_agent/agent_factory.py` | Adjust for Handoff |
| `front/agent_web_ui/src/App.vue` | Login/Token handling |

### Removed Files (1)
| File | Reason |
|------|--------|
| `docker/langfuse/docker-compose.yml` | Merged into main compose |
