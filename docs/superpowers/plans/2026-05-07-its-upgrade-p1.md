# ITS Multi-Agent P1 Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Containerize all services with Docker Compose, add JWT authentication, and enable Agent Handoff dual-mode.

**Architecture:** Single docker-compose.yml with 8 services (MySQL, Backend, Knowledge, 2 frontends, Nginx proxy, Langfuse). JWT auth with passlib[bcrypt] + python-jose. Handoff via openai-agents SDK `handoff()` alongside existing Tool Calling.

**Tech Stack:** Docker, Nginx, FastAPI OAuth2, passlib, python-jose, openai-agents SDK, Vue 3

---

## Phase 1: Docker Containerization

### Task 1: Create Backend Dockerfile

**Files:**
- Create: `docker/backend.Dockerfile`

- [ ] **Step 1: Create Dockerfile**

Create `docker/backend.Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app/ .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api.main:create_fast_api", "--host", "0.0.0.0", "--port", "8000", "--factory"]
```

- [ ] **Step 2: Commit**

```bash
git add docker/backend.Dockerfile
git commit -m "docker: add backend Dockerfile"
```

---

### Task 2: Create Knowledge Service Dockerfile

**Files:**
- Create: `docker/knowledge.Dockerfile`

- [ ] **Step 1: Create Dockerfile**

Create `docker/knowledge.Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/knowledge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/knowledge/ .

# Copy knowledge data
COPY backend/knowledge/data/ ./data/
COPY backend/knowledge/chroma_kb1/ ./chroma_kb1/

# Expose port
EXPOSE 8001

# Run the application
CMD ["uvicorn", "api.main:create_fast_api", "--host", "0.0.0.0", "--port", "8001", "--factory"]
```

- [ ] **Step 2: Commit**

```bash
git add docker/knowledge.Dockerfile
git commit -m "docker: add knowledge service Dockerfile"
```

---

### Task 3: Create Frontend Dockerfiles

**Files:**
- Create: `docker/frontend-agent.Dockerfile`
- Create: `docker/frontend-knowledge.Dockerfile`

- [ ] **Step 1: Create Agent Web UI Dockerfile**

Create `docker/frontend-agent.Dockerfile`:

```dockerfile
# Build stage
FROM node:18-alpine AS build
WORKDIR /app
COPY front/agent_web_ui/package*.json ./
RUN npm ci
COPY front/agent_web_ui/ .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx/agent-web-ui.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 2: Create Knowledge UI Dockerfile**

Create `docker/frontend-knowledge.Dockerfile`:

```dockerfile
# Build stage
FROM node:18-alpine AS build
WORKDIR /app
COPY front/knowlege_platform_ui/package*.json ./
RUN npm ci
COPY front/knowlege_platform_ui/ .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx/knowledge-ui.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 3: Commit**

```bash
git add docker/frontend-agent.Dockerfile docker/frontend-knowledge.Dockerfile
git commit -m "docker: add frontend Dockerfiles with multi-stage build"
```

---

### Task 4: Create Nginx Configuration

**Files:**
- Create: `docker/nginx/agent-web-ui.conf`
- Create: `docker/nginx/knowledge-ui.conf`
- Create: `docker/nginx/default.conf`

- [ ] **Step 1: Create Agent Web UI Nginx config**

Create `docker/nginx/agent-web-ui.conf`:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 2: Create Knowledge UI Nginx config**

Create `docker/nginx/knowledge-ui.conf`:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 3: Create main proxy Nginx config**

Create `docker/nginx/default.conf`:

```nginx
upstream backend {
    server backend:8000;
}

upstream knowledge {
    server knowledge:8001;
}

upstream agent-web-ui {
    server agent-web-ui:80;
}

upstream knowledge-ui {
    server knowledge-ui:80;
}

server {
    listen 80;
    server_name localhost;

    # Agent Web UI (Vue SPA)
    location / {
        proxy_pass http://agent-web-ui;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Knowledge Platform UI (Vue SPA)
    location /knowledge {
        proxy_pass http://knowledge-ui;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # Knowledge Service API
    location /knowledge-api/ {
        proxy_pass http://knowledge/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add docker/nginx/
git commit -m "docker: add Nginx reverse proxy configuration"
```

---

### Task 5: Create docker-compose.yml

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.docker`

- [ ] **Step 1: Create docker-compose.yml**

Create `docker-compose.yml` at project root:

```yaml
services:
  mysql:
    image: mysql:8.0
    container_name: its-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_PASSWORD:-root}
      MYSQL_DATABASE: ${MYSQL_DATABASE:-its_db}
    volumes:
      - mysql-data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - its-network

  langfuse-db:
    image: postgres:15-alpine
    container_name: its-langfuse-db
    environment:
      POSTGRES_USER: langfuse
      POSTGRES_PASSWORD: langfuse_secret
      POSTGRES_DB: langfuse
    volumes:
      - langfuse-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - its-network

  langfuse-server:
    image: langfuse/langfuse:latest
    container_name: its-langfuse-server
    ports:
      - "3001:3000"
    environment:
      DATABASE_URL: postgresql://langfuse:langfuse_secret@langfuse-db:5432/langfuse
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET:-its-multi-agent-secret}
      NEXTAUTH_URL: http://localhost:3001
      SALT: ${LANGFUSE_SALT:-its-multi-agent-salt}
    depends_on:
      langfuse-db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - its-network

  backend:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    container_name: its-backend
    ports:
      - "8000:8000"
    env_file:
      - backend/app/.env
    environment:
      MYSQL_HOST: mysql
      KNOWLEDGE_BASE_URL: http://knowledge:8001
      LANGFUSE_HOST: http://langfuse-server:3000
    depends_on:
      mysql:
        condition: service_healthy
      knowledge:
        condition: service_started
    restart: unless-stopped
    networks:
      - its-network

  knowledge:
    build:
      context: .
      dockerfile: docker/knowledge.Dockerfile
    container_name: its-knowledge
    ports:
      - "8001:8001"
    env_file:
      - backend/knowledge/.env
    environment:
      MYSQL_HOST: mysql
    volumes:
      - chroma-data:/app/chroma_kb1
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - its-network

  agent-web-ui:
    build:
      context: .
      dockerfile: docker/frontend-agent.Dockerfile
    container_name: its-agent-web-ui
    restart: unless-stopped
    networks:
      - its-network

  knowledge-ui:
    build:
      context: .
      dockerfile: docker/frontend-knowledge.Dockerfile
    container_name: its-knowledge-ui
    restart: unless-stopped
    networks:
      - its-network

  nginx-proxy:
    image: nginx:alpine
    container_name: its-nginx
    ports:
      - "80:80"
    volumes:
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - backend
      - knowledge
      - agent-web-ui
      - knowledge-ui
    restart: unless-stopped
    networks:
      - its-network

volumes:
  mysql-data:
  langfuse-db-data:
  chroma-data:

networks:
  its-network:
    driver: bridge
```

- [ ] **Step 2: Create .env.docker template**

Create `.env.docker`:

```
# MySQL
MYSQL_PASSWORD=root
MYSQL_DATABASE=its_db

# Langfuse
LANGFUSE_NEXTAUTH_SECRET=its-multi-agent-secret
LANGFUSE_SALT=its-multi-agent-salt
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .env.docker
git commit -m "docker: add main docker-compose.yml with all services"
```

---

## Phase 2: JWT Authentication

### Task 6: Add JWT Settings and Dependencies

**Files:**
- Modify: `backend/app/config/settings.py:85-88`
- Modify: `backend/app/requirements.txt`

- [ ] **Step 1: Add JWT settings**

In `backend/app/config/settings.py`, add after the Langfuse config section (after line 88):

```python
    # ==================== JWT 认证配置 ====================

    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="JWT 签名密钥"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT 签名算法"
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access Token 有效期（分钟）"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh Token 有效期（天）"
    )
```

- [ ] **Step 2: Add auth dependencies**

Append to `backend/app/requirements.txt`:

```
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/config/settings.py backend/app/requirements.txt
git commit -m "feat: add JWT configuration and auth dependencies"
```

---

### Task 7: Create User Model

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`

- [ ] **Step 1: Create models package**

Create `backend/app/models/__init__.py`:

```python
```

- [ ] **Step 2: Create User model**

Create `backend/app/models/user.py`:

```python
from infrastructure.database.database_pool import db_pool
from infrastructure.logging.logger import logger


def init_users_table():
    """Create users table if it doesn't exist."""
    conn = None
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("Users table initialized")
    except Exception as e:
        logger.error(f"Failed to create users table: {e}")
        raise
    finally:
        if conn:
            db_pool.release_connection(conn)


def get_user_by_username(username: str) -> dict | None:
    """Get user by username."""
    conn = None
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, hashed_password, is_active FROM users WHERE username = %s",
            (username,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "hashed_password": row[3],
                "is_active": bool(row[4]),
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get user by username: {e}")
        return None
    finally:
        if conn:
            db_pool.release_connection(conn)


def create_user(username: str, email: str, hashed_password: str) -> dict | None:
    """Create a new user and return user info."""
    conn = None
    try:
        conn = db_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (%s, %s, %s)",
            (username, email, hashed_password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        logger.info(f"User created: {username} (id={user_id})")
        return {"id": user_id, "username": username, "email": email}
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        return None
    finally:
        if conn:
            db_pool.release_connection(conn)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/
git commit -m "feat: add User model with MySQL persistence"
```

---

### Task 8: Create Auth Service

**Files:**
- Create: `backend/app/services/auth_service.py`

- [ ] **Step 1: Create auth service**

Create `backend/app/services/auth_service.py`:

```python
from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from jose import JWTError, jwt

from config.settings import settings
from models.user import get_user_by_username, create_user
from infrastructure.logging.logger import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        return None


def register_user(username: str, email: str, password: str) -> dict:
    """Register a new user."""
    # Check if username already exists
    existing = get_user_by_username(username)
    if existing:
        return {"success": False, "error": "用户名已存在"}

    hashed = hash_password(password)
    user = create_user(username, email, hashed)
    if user:
        return {"success": True, "user": user}
    return {"success": False, "error": "注册失败，请稍后重试"}


def login_user(username: str, password: str) -> dict:
    """Authenticate user and return tokens."""
    user = get_user_by_username(username)
    if not user:
        return {"success": False, "error": "用户名或密码错误"}

    if not user["is_active"]:
        return {"success": False, "error": "账号已被禁用"}

    if not verify_password(password, user["hashed_password"]):
        return {"success": False, "error": "用户名或密码错误"}

    # Create tokens
    token_data = {"user_id": user["id"], "username": user["username"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {"id": user["id"], "username": user["username"]},
    }


def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an access token using a refresh token."""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return {"success": False, "error": "无效的刷新令牌"}

    # Create new access token
    token_data = {"user_id": payload["user_id"], "username": payload["username"]}
    new_access_token = create_access_token(token_data)

    return {
        "success": True,
        "access_token": new_access_token,
        "token_type": "bearer",
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/auth_service.py
git commit -m "feat: add auth service with JWT token management"
```

---

### Task 9: Create Auth Router

**Files:**
- Create: `backend/app/api/auth_router.py`

- [ ] **Step 1: Create auth router**

Create `backend/app/api/auth_router.py`:

```python
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional

from services.auth_service import register_user, login_user, refresh_access_token, decode_token
from infrastructure.logging.logger import logger

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ==================== Request Models ====================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ==================== Dependency ====================

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract and validate user from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="无效的访问令牌")

    return {"user_id": payload["user_id"], "username": payload["username"]}


# ==================== Routes ====================

@router.post("/register", summary="用户注册")
async def register(request: RegisterRequest):
    """Register a new user."""
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度不能少于6位")

    result = register_user(request.username, request.email, request.password)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"success": True, "message": "注册成功", "user": result["user"]}


@router.post("/login", summary="用户登录")
async def login(request: LoginRequest):
    """Login and get access + refresh tokens."""
    result = login_user(request.username, request.password)

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])

    return result


@router.post("/refresh", summary="刷新令牌")
async def refresh(request: RefreshRequest):
    """Refresh access token using refresh token."""
    result = refresh_access_token(request.refresh_token)

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])

    return result


@router.get("/me", summary="获取当前用户")
async def me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {"success": True, "user": current_user}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/auth_router.py
git commit -m "feat: add auth API router with register/login/refresh/me"
```

---

### Task 10: Register Auth Router and Protect Existing Routes

**Files:**
- Modify: `backend/app/api/main.py:5,52`
- Modify: `backend/app/api/routers.py:5-7,15`

- [ ] **Step 1: Register auth router in main.py**

In `backend/app/api/main.py`, add the auth router import after line 5:

```python
from api.routers import router
from api.auth_router import router as auth_router
```

And register it after line 52 (after `app.include_router(router=router)`):

```python
    app.include_router(router=auth_router)
```

- [ ] **Step 2: Add auth dependency to existing routes**

In `backend/app/api/routers.py`, add import after line 5:

```python
from api.auth_router import get_current_user
from fastapi import Depends
```

And add auth dependency to the query endpoint (line 15):

```python
@router.post("/api/query", summary="智能体对话接口")
async def query(request_context: ChatMessageRequest, current_user: dict = Depends(get_current_user)) -> StreamingResponse:
```

And to the sessions endpoint (line 44):

```python
@router.post("/api/user_sessions")
def get_user_sessions(request: UserSessionsRequest, current_user: dict = Depends(get_current_user)):
```

- [ ] **Step 3: Initialize users table on startup**

In `backend/app/api/main.py`, add import and init call in the lifespan function:

```python
from models.user import init_users_table
```

Add after MCP connection in lifespan (after line 24):

```python
    try:
        init_users_table()
        logger.info("用户表初始化完成")
    except Exception as e:
        logger.error(f"用户表初始化失败: {str(e)}")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/main.py backend/app/api/routers.py
git commit -m "feat: register auth router and protect API routes with JWT"
```

---

### Task 11: Update Frontend for JWT Authentication

**Files:**
- Modify: `front/agent_web_ui/src/App.vue`

- [ ] **Step 1: Update login to call API**

In `front/agent_web_ui/src/App.vue`, replace the `handleLogin` function (lines 397-424) with:

```javascript
    // 处理登录
    const handleLogin = async () => {
      loginError.value = '';

      try {
        const response = await fetch('http://127.0.0.1:8000/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: username.value, password: password.value })
        });

        if (!response.ok) {
          const error = await response.json();
          loginError.value = error.detail || '用户名或密码错误';
          return;
        }

        const data = await response.json();
        isLoggedIn.value = true;
        currentUser.value = data.user.username;
        localStorage.setItem('accessToken', data.access_token);
        localStorage.setItem('refreshToken', data.refresh_token);
        localStorage.setItem('currentUserId', data.user.username);
        window.scrollTo(0, 0);
        username.value = '';
        password.value = '';
      } catch (error) {
        loginError.value = '登录失败，请检查网络连接';
      }
    };
```

- [ ] **Step 2: Add token to API requests**

Replace the fetch calls to include Authorization header. Find the `fetchSessions` function (around line 434) and update:

```javascript
        const response = await fetch('http://127.0.0.1:8000/api/user_sessions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          },
          body: JSON.stringify({"user_id": currentUser.value})
        });
```

Find the query fetch (around line 623) and update:

```javascript
          const response = await fetch('http://127.0.0.1:8000/api/query', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            },
            body: JSON.stringify(requestData)
          });
```

- [ ] **Step 3: Update logout to clear tokens**

In the `handleLogout` function (around line 533), add token cleanup:

```javascript
    const handleLogout = () => {
      isLoggedIn.value = false;
      currentUser.value = '';
      localStorage.removeItem('currentUserId');
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      // ... rest of existing cleanup
    };
```

- [ ] **Step 4: Update session restore to check token**

Replace the session restore logic (around lines 306-321) with:

```javascript
    // 初始化时检查localStorage中的token
    const savedToken = localStorage.getItem('accessToken');
    const savedUserId = localStorage.getItem('currentUserId');
    if (savedToken && savedUserId) {
      // Verify token by calling /me endpoint
      fetch('http://127.0.0.1:8000/api/auth/me', {
        headers: { 'Authorization': `Bearer ${savedToken}` }
      }).then(res => {
        if (res.ok) {
          currentUser.value = savedUserId;
          isLoggedIn.value = true;
        } else {
          // Token expired, clear
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          localStorage.removeItem('currentUserId');
        }
      }).catch(() => {
        // Network error, keep logged in state
        currentUser.value = savedUserId;
        isLoggedIn.value = true;
      });
    }
```

- [ ] **Step 5: Remove hardcoded test users**

Remove the hardcoded user lists from `handleLogin` and the session restore block. The login hint in the template can be updated:

```html
        <div class="login-hint">
          <p>请使用注册的账号登录</p>
        </div>
```

- [ ] **Step 6: Commit**

```bash
git add front/agent_web_ui/src/App.vue
git commit -m "feat: integrate JWT authentication in frontend"
```

---

## Phase 3: Agent Handoff Upgrade

### Task 12: Create Orchestrator v2 Prompt

**Files:**
- Create: `backend/app/prompts/orchestrator_v2.md`

- [ ] **Step 1: Create orchestrator v2 prompt**

Create `backend/app/prompts/orchestrator_v2.md` with the full v1 content plus the following section appended before the "成功关键" section:

```markdown
## 🔄 Handoff 决策规则

### 使用 Tool Calling（默认模式）
适用于以下场景：
- 用户问题明确，单轮即可回答
- 信息查询类（天气、股价、知识库查询）
- 简单的服务站查询或 POI 导航
- 用户没有表达需要进一步帮助的意愿

### 使用 Handoff（转交模式）
适用于以下场景：
- **故障排查**：需要多轮交互逐步诊断（如"开不了机"→"检查电源"→"看指示灯"→"还是不行"）
- **需求不明确**：用户表达模糊，需要子 Agent 追问澄清
- **复杂多步骤**：需要子 Agent 持续跟进并多次调用工具
- **用户明确要求**：用户说"帮我一步步排查"或"详细指导我"

### 决策示例

**用户**："我的电脑开不了机"
- ❌ Tool Calling：调用技术专家获取一段文字回答
- ✅ Handoff：转交技术专家，让它与用户逐步排查

**用户**："今天天气怎么样"
- ✅ Tool Calling：调用技术专家获取天气信息
- ❌ Handoff：不需要多轮交互

**用户**："帮我找最近的维修站，然后导航过去"
- ✅ Handoff：转交服务站专家，让它处理多步骤任务

### 关键原则
1. **默认使用 Tool Calling**，仅在明确需要多轮交互时使用 Handoff
2. Handoff 后编排器等待子 Agent 完成并返回结果
3. 不要对简单查询使用 Handoff（过度使用会降低效率）
```

Also copy the full v1 content and integrate this section naturally.

- [ ] **Step 2: Commit**

```bash
git add backend/app/prompts/orchestrator_v2.md
git commit -m "feat: add orchestrator v2 prompt with Handoff decision rules"
```

---

### Task 13: Update Orchestrator Agent with Handoffs

**Files:**
- Modify: `backend/app/multi_agent/orchestrator_agent.py:1-12`

- [ ] **Step 1: Add handoff import and configuration**

Replace the imports and agent definition in `backend/app/multi_agent/orchestrator_agent.py`:

```python
import asyncio
from agents import (
    Agent,
    ModelSettings,
    Runner,
    handoff,
)
from infrastructure.ai.openai_client import sub_model
from infrastructure.ai.openai_client import main_model
from infrastructure.ai.prompt_loader import load_prompt
from multi_agent.agent_factory import AGENT_TOOLS
from multi_agent.technical_agent import technical_agent
from multi_agent.service_agent import comprehensive_service_agent
from infrastructure.tools.mcp.mcp_servers import search_mcp_client, baidu_mcp_client
from contextlib import AsyncExitStack

# 1. 创建主调度智能体（支持 Tool Calling + Handoff 双模式）
orchestrator_agent = Agent(
    name="主调度智能体",
    instructions=load_prompt("orchestrator_v2"),
    model=sub_model,
    tools=AGENT_TOOLS,
    handoffs=[
        handoff(technical_agent),
        handoff(comprehensive_service_agent),
    ],
)
```

Keep the rest of the file (test functions) unchanged.

- [ ] **Step 2: Commit**

```bash
git add backend/app/multi_agent/orchestrator_agent.py
git commit -m "feat: add Handoff support to orchestrator agent"
```

---

### Task 14: Update agent_factory for Handoff Compatibility

**Files:**
- Modify: `backend/app/multi_agent/agent_factory.py:1-9`

- [ ] **Step 1: Add handoff export**

In `backend/app/multi_agent/agent_factory.py`, add the handoff import after line 3:

```python
from agents import function_tool, Runner, handoff
```

And add a HANDOFF_TARGETS export after the AGENT_TOOLS list:

```python
# 4. Handoff 目标（供编排器使用）
HANDOFF_TARGETS = [
    technical_agent,
    comprehensive_service_agent,
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/multi_agent/agent_factory.py
git commit -m "feat: add Handoff target exports for orchestrator"
```

---

## Final Verification

### Task 15: Verify All Changes

- [ ] **Step 1: Check git status**

```bash
git status
git log --oneline feature/p0-upgrade-langfuse-rag --not main
```

- [ ] **Step 2: Verify file structure**

```bash
ls docker/
ls backend/app/models/
ls backend/app/api/auth_router.py
ls backend/app/prompts/orchestrator_v2.md
```

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: P1 upgrade complete - Docker, JWT auth, Agent Handoff"
```
