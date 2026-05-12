# ITS Multi-Agent 企业级升级 — 设计与实现文档

> **版本**: v1.0  
> **日期**: 2026-05-12  
> **范围**: Agent 系统、RAG 系统、工程基础设施  
> **优先级**: P0 → P1 → P2，按顺序实施

---

## 目录

- [P0-1: Orchestrator 使用 main_model](#p0-1-orchestrator-使用-main_model)
- [P0-2: 恢复完整 Langfuse 追踪链路](#p0-2-恢复完整-langfuse-追踪链路)
- [P0-3: 前端 API 地址环境变量化](#p0-3-前端-api-地址环境变量化)
- [P0-4: JWT 密钥安全启动校验](#p0-4-jwt-密钥安全启动校验)
- [P1-1: Agent 输入/输出 Guardrails](#p1-1-agent-输入输出-guardrails)
- [P1-2: BM25 索引持久化与标题元数据缓存](#p1-2-bm25-索引持久化与标题元数据缓存)
- [P1-3: 售后 Agent 对接 MySQL 真实数据](#p1-3-售后-agent-对接-mysql-真实数据)
- [P1-4: 对话上下文智能压缩](#p1-4-对话上下文智能压缩)
- [P2-1: Markdown 语义分块](#p2-1-markdown-语义分块)
- [P2-2: RAG 查询路由器](#p2-2-rag-查询路由器)
- [P2-3: Agent 结构化输出](#p2-3-agent-结构化输出)
- [P2-4: API 限流](#p2-4-api-限流)
- [P2-5: 健康检查端点](#p2-5-健康检查端点)
- [P2-6: 检索质量反馈闭环](#p2-6-检索质量反馈闭环)

---

## P0-1: Orchestrator 使用 main_model

### 背景

当前所有 Agent（包括负责意图识别和任务拆解的 Orchestrator）都使用 `sub_model`。`openai_client.py` 中已定义了 `main_model`（MiMo-V2.5-Pro），但从未被使用。Orchestrator 承担最关键的路由判断，应使用更强的模型。

### 当前代码

**文件**: `backend/app/multi_agent/orchestrator_agent.py`

```python
# 第3行
from infrastructure.ai.openai_client import sub_model

# 第10-15行
orchestrator_agent = Agent(
    name="orchestrator",
    instructions=load_prompt("orchestrator_v2"),
    model=sub_model,      # ← 问题：使用了弱模型
    tools=AGENT_TOOLS,
)
```

### 目标代码

```python
from infrastructure.ai.openai_client import main_model

orchestrator_agent = Agent(
    name="orchestrator",
    instructions=load_prompt("orchestrator_v2"),
    model=main_model,     # ← 改为强模型
    tools=AGENT_TOOLS,
)
```

### 实现步骤

1. 打开 `backend/app/multi_agent/orchestrator_agent.py`
2. 将第 3 行的 `from infrastructure.ai.openai_client import sub_model` 改为 `from infrastructure.ai.openai_client import main_model`
3. 将第 13 行的 `model=sub_model` 改为 `model=main_model`
4. 子 Agent（technical_agent.py、service_agent.py、after_sales_agent.py）保持 `sub_model` 不变

### 验证

- 启动后端服务，发送一条包含多任务的消息（如"查小米股价，然后导航去最近服务站"），确认 Orchestrator 能正确拆解为两个工具调用
- 检查 Langfuse 中 Orchestrator 的 model 字段已变为 main_model 对应的模型名

---

## P0-2: 恢复完整 Langfuse 追踪链路

### 背景

当前 `agent_factory.py` 中三个 Agent Tool 在调用子 Agent 时传入了 `RunConfig(tracing_disabled=True)`，导致 Langfuse 只能看到 Orchestrator 级别的 trace，无法追踪子 Agent 内部的工具调用链和耗时。`agent_service.py` 中 Orchestrator 自身的 `Runner.run_streamed` 也传入了 `tracing_disabled=True`。

### 当前代码

**文件**: `backend/app/multi_agent/agent_factory.py`，共 3 处：

```python
# 第57行（consult_technical_expert 内）
result = await Runner.run(
    technical_agent,
    input=query,
    run_config=RunConfig(tracing_disabled=True)  # ← 禁用了追踪
)

# 第91行（query_service_station_and_navigate 内）
result = await Runner.run(
    comprehensive_service_agent,
    input=query,
    run_config=RunConfig(tracing_disabled=True)  # ← 禁用了追踪
)

# 第131行（consult_after_sales_expert 内）
result = await Runner.run(
    after_sales_agent,
    input=query,
    run_config=RunConfig(tracing_disabled=True)  # ← 禁用了追踪
)
```

**文件**: `backend/app/services/agent_service.py`：

```python
# 第50-55行
streaming_result = Runner.run_streamed(
    starting_agent=orchestrator_agent,
    input=chat_history,
    max_turns=10,
    run_config=RunConfig(tracing_disabled=True)  # ← 禁用了追踪
)
```

**文件**: `backend/app/multi_agent/service_agent.py`，第 1-3 行：

```python
from agents import set_tracing_disabled
set_tracing_disabled(True)  # ← 全局禁用了追踪
```

### 实现步骤

1. **`backend/app/multi_agent/agent_factory.py`**：在三个 `_run` 函数中，移除 `run_config=RunConfig(tracing_disabled=True)` 参数，改为不传 `run_config`（使用默认值）：
   ```python
   # 修改后（三处相同逻辑）
   result = await Runner.run(
       technical_agent,
       input=query,
   )
   ```
   同时移除文件顶部的 `from agents.run import RunConfig` 导入（如果只有这里使用）。

2. **`backend/app/services/agent_service.py`**：移除 `run_config` 参数：
   ```python
   streaming_result = Runner.run_streamed(
       starting_agent=orchestrator_agent,
       input=chat_history,
       max_turns=10,
   )
   ```
   同时移除第 3 行的 `from agents.run import Runner, RunConfig` 中的 `RunConfig`（改为 `from agents.run import Runner`），或保留 import 如果其他地方用到。

3. **`backend/app/multi_agent/service_agent.py`**：删除文件开头两行：
   ```python
   # 删除这两行
   from agents import set_tracing_disabled
   set_tracing_disabled(True)
   ```

### 验证

- 发送一条技术咨询消息，然后检查 Langfuse Dashboard
- 应看到完整的调用树：orchestrator → consult_technical_expert → technical_expert（子Agent）→ query_knowledge / bailian_web_search
- 每层都应有耗时记录

---

## P0-3: 前端 API 地址环境变量化

### 背景

`chat.js` 和 `auth.js` 中硬编码了 `const API_BASE = 'http://127.0.0.1:8000'`，部署到测试/生产环境时必须手动修改源码。

### 当前代码

**文件**: `front/agent_web_ui/src/stores/chat.js` 第 5 行
**文件**: `front/agent_web_ui/src/stores/auth.js` 第 4 行

```javascript
const API_BASE = 'http://127.0.0.1:8000'
```

### 实现步骤

1. **创建环境变量文件** `front/agent_web_ui/.env`：
   ```
   VITE_API_BASE=http://127.0.0.1:8000
   ```

2. **创建生产环境变量文件** `front/agent_web_ui/.env.production`：
   ```
   VITE_API_BASE=
   ```
   留空表示使用相对路径（通过 Nginx 反向代理）。

3. **修改 `front/agent_web_ui/src/stores/chat.js`** 第 5 行：
   ```javascript
   const API_BASE = import.meta.env.VITE_API_BASE || ''
   ```

4. **修改 `front/agent_web_ui/src/stores/auth.js`** 第 4 行：
   ```javascript
   const API_BASE = import.meta.env.VITE_API_BASE || ''
   ```

5. **更新 `.gitignore`**：确保 `.env.local` 被忽略（Vite 默认加载 `.env.local`）：
   ```
   # 确认已有或添加
   .env.local
   .env.*.local
   ```

### 验证

- 本地 `npm run dev` 启动后正常请求 `http://127.0.0.1:8000`
- `npm run build` 后检查产物中不包含硬编码地址
- 设置 `VITE_API_BASE=http://other-host:8000` 后重启 dev 服务器，确认请求指向新地址

---

## P0-4: JWT 密钥安全启动校验

### 背景

`settings.py` 中 `JWT_SECRET_KEY` 默认值为 `"change-me-in-production"`。如果部署时忘记配置，所有 JWT 都可以被伪造。

### 当前代码

**文件**: `backend/app/config/settings.py` 第 92-95 行：

```python
JWT_SECRET_KEY: str = Field(
    default="change-me-in-production",
    description="JWT 签名密钥"
)
```

### 实现步骤

在 `Settings` 类的 `model_validator` 中添加 JWT 密钥检查。修改 `backend/app/config/settings.py`：

在已有的 `check_ai_service_configuration` 验证器之后，添加新的验证逻辑（直接在同一个验证器中追加即可）：

```python
@model_validator(mode='after')
def check_ai_service_configuration(self) -> Self:
    # --- 原有的 AI 服务检查 ---
    has_service = any([
        self.MAIN_API_KEY and self.MAIN_BASE_URL,
        self.SUB_API_KEY and self.SUB_BASE_URL
    ])
    if not has_service:
        raise ValueError("必须配置至少一个 AI 服务 (主模型或子模型)")

    # --- 新增：JWT 密钥检查 ---
    import logging
    _logger = logging.getLogger("config")
    INSECURE_DEFAULTS = {"change-me-in-production", "secret", "test", ""}
    if self.JWT_SECRET_KEY in INSECURE_DEFAULTS:
        _logger.warning(
            "⚠️  JWT_SECRET_KEY 使用了不安全的默认值，"
            "请在 .env 中配置一个至少 32 字符的随机密钥。"
            "生产环境中此配置将导致安全漏洞。"
        )

    return self
```

**说明**：使用 WARNING 而非直接 raise，避免开发环境无法启动。如果希望生产环境强制检查，可通过添加一个 `ENVIRONMENT` 配置项来区分：

```python
ENVIRONMENT: str = Field(default="development", description="运行环境")

# 在验证器中：
if self.ENVIRONMENT == "production" and self.JWT_SECRET_KEY in INSECURE_DEFAULTS:
    raise ValueError("生产环境必须配置安全的 JWT_SECRET_KEY")
```

### 验证

- 不配置 JWT_SECRET_KEY 启动后端，应在日志中看到 WARNING
- 在 `.env` 中配置 `JWT_SECRET_KEY=a-random-32-char-string-here!!!` 后启动，WARNING 消失

---

## P1-1: Agent 输入/输出 Guardrails

### 背景

当前系统对用户输入没有任何安全过滤，对 Agent 输出也没有质量控制。openai-agents SDK 原生支持 `input_guardrails` 和 `output_guardrails` 参数。需要实现：
- **输入护栏**：检测 prompt 注入、敏感词、超长输入
- **输出护栏**：检测幻觉（回答是否基于工具结果）、敏感信息泄漏

### 新建文件

**文件**: `backend/app/multi_agent/guardrails.py`

```python
"""
Agent Guardrails — 输入/输出安全护栏

使用 openai-agents SDK 的 GuardrailFunctionOutput / InputGuardrail / OutputGuardrail 实现。
"""

from agents import (
    GuardrailFunctionOutput,
    InputGuardrail,
    OutputGuardrail,
    RunContextWrapper,
    Agent,
    Runner,
    TResponseInputItem,
)
from infrastructure.logging.logger import logger
from infrastructure.ai.openai_client import sub_model
from pydantic import BaseModel
import re
from typing import List


# ============================================================
# 1. 输入护栏：Prompt 注入检测
# ============================================================

# 1.1 基于规则的快速检测
INJECTION_PATTERNS = [
    r"忽略.*(?:之前|以上|所有).*(?:指令|规则|提示)",
    r"ignore.*(?:previous|above|all).*(?:instructions?|rules?|prompts?)",
    r"你(?:现在|从现在)是.*(?:角色|模式)",
    r"system\s*(?:prompt|message)",
    r"(?:jailbreak|越狱|DAN|developer\s*mode)",
    r"(?:假装|pretend|act\s+as).*(?:你是|you\s+are)",
    r"(?:不要|不需要|don'?t).*(?:遵守|遵循|follow).*(?:规则|限制|rules?)",
]
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

# 1.2 输入长度限制
MAX_INPUT_LENGTH = 2000

# 1.3 敏感词列表（示例，实际部署时应从配置或数据库加载）
SENSITIVE_KEYWORDS = [
    "身份证号", "银行卡", "密码", "信用卡",
    "社保号", "护照号",
]


async def input_guardrail_fn(
    ctx: RunContextWrapper,
    agent: Agent,
    input: str | List[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """
    输入护栏函数。检测：
    1. Prompt 注入攻击
    2. 超长输入
    3. 敏感词

    返回 GuardrailFunctionOutput(output_info=..., tripwire_triggered=True/False)
    tripwire_triggered=True 时 Agent 会拒绝处理此输入。
    """
    # 将输入标准化为字符串
    if isinstance(input, list):
        text_parts = []
        for item in input:
            if isinstance(item, dict) and "content" in item:
                text_parts.append(str(item["content"]))
            elif isinstance(item, str):
                text_parts.append(item)
        text = " ".join(text_parts)
    else:
        text = str(input)

    # 检查 1：输入长度
    if len(text) > MAX_INPUT_LENGTH:
        logger.warning(f"[Guardrail] 输入超长: {len(text)} 字符")
        return GuardrailFunctionOutput(
            output_info={"reason": "input_too_long", "length": len(text)},
            tripwire_triggered=True,
        )

    # 检查 2：Prompt 注入模式
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            logger.warning(f"[Guardrail] 检测到 Prompt 注入: {pattern.pattern}")
            return GuardrailFunctionOutput(
                output_info={"reason": "prompt_injection", "pattern": pattern.pattern},
                tripwire_triggered=True,
            )

    # 检查 3：敏感词
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in text:
            logger.warning(f"[Guardrail] 检测到敏感词: {keyword}")
            return GuardrailFunctionOutput(
                output_info={"reason": "sensitive_content", "keyword": keyword},
                tripwire_triggered=True,
            )

    return GuardrailFunctionOutput(
        output_info={"reason": "passed"},
        tripwire_triggered=False,
    )


# ============================================================
# 2. 输出护栏：幻觉检测 + 敏感信息泄漏
# ============================================================

# 2.1 不应出现在输出中的敏感信息模式
OUTPUT_SENSITIVE_PATTERNS = [
    r"\b\d{17}[\dXx]\b",                   # 身份证号
    r"\b\d{16,19}\b",                       # 银行卡号（16-19位纯数字）
    r"\b(?:API[_\s]?KEY|api[_\s]?key)\s*[:=]\s*\S+",  # API Key 泄漏
]
COMPILED_OUTPUT_PATTERNS = [re.compile(p) for p in OUTPUT_SENSITIVE_PATTERNS]


async def output_guardrail_fn(
    ctx: RunContextWrapper,
    agent: Agent,
    output: str,
) -> GuardrailFunctionOutput:
    """
    输出护栏函数。检测：
    1. 输出中的敏感信息模式（身份证号、银行卡号等）

    注意：幻觉检测（判断回答是否基于工具返回内容）需要 LLM 评估，
    成本较高，可以通过异步采样方式实现，不在此同步护栏中处理。
    """
    if not output:
        return GuardrailFunctionOutput(
            output_info={"reason": "empty_output"},
            tripwire_triggered=False,
        )

    # 检查敏感信息泄漏
    for pattern in COMPILED_OUTPUT_PATTERNS:
        if pattern.search(output):
            logger.warning(f"[Guardrail] 输出包含敏感信息模式: {pattern.pattern}")
            return GuardrailFunctionOutput(
                output_info={"reason": "sensitive_output", "pattern": pattern.pattern},
                tripwire_triggered=True,
            )

    return GuardrailFunctionOutput(
        output_info={"reason": "passed"},
        tripwire_triggered=False,
    )


# ============================================================
# 3. 构建 Guardrail 对象（供 Agent 定义使用）
# ============================================================

input_guardrail = InputGuardrail(guardrail_function=input_guardrail_fn)
output_guardrail = OutputGuardrail(guardrail_function=output_guardrail_fn)
```

### 修改 Orchestrator Agent 定义

**文件**: `backend/app/multi_agent/orchestrator_agent.py`

在 Agent 创建时添加 guardrails 参数：

```python
from multi_agent.guardrails import input_guardrail, output_guardrail

orchestrator_agent = Agent(
    name="orchestrator",
    instructions=load_prompt("orchestrator_v2"),
    model=main_model,
    tools=AGENT_TOOLS,
    input_guardrails=[input_guardrail],
    output_guardrails=[output_guardrail],
)
```

### 修改 agent_service.py 处理护栏触发

**文件**: `backend/app/services/agent_service.py`

在 `process_task` 的 try-except 中添加对 `InputGuardrailTripwireTriggered` 和 `OutputGuardrailTripwireTriggered` 异常的捕获：

```python
from agents.exceptions import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered

# 在 try 块的异常处理中添加（在现有 except Exception 之前）：
except InputGuardrailTripwireTriggered as e:
    logger.warning(f"输入护栏触发: {e.guardrail_result.output_info}")
    reason = e.guardrail_result.output_info.get("reason", "unknown")
    if reason == "prompt_injection":
        msg = "检测到不安全的输入内容，请重新描述您的问题。"
    elif reason == "input_too_long":
        msg = "输入内容过长，请精简后重试（最多2000字）。"
    elif reason == "sensitive_content":
        msg = "请勿在对话中发送敏感个人信息。"
    else:
        msg = "输入内容不符合安全要求，请重新描述。"
    yield "data: " + ResponseFactory.build_text(
        msg, ContentKind.ANSWER
    ).model_dump_json() + "\n\n"
    yield "data: " + ResponseFactory.build_finish().model_dump_json() + "\n\n"

except OutputGuardrailTripwireTriggered as e:
    logger.warning(f"输出护栏触发: {e.guardrail_result.output_info}")
    msg = "系统检测到回复内容可能包含敏感信息，已自动过滤。请重新提问。"
    yield "data: " + ResponseFactory.build_text(
        msg, ContentKind.ANSWER
    ).model_dump_json() + "\n\n"
    yield "data: " + ResponseFactory.build_finish().model_dump_json() + "\n\n"
```

### 验证

- 发送包含 "忽略之前所有指令" 的消息 → 应返回安全拦截提示
- 发送超过 2000 字的消息 → 应返回长度限制提示
- 正常消息不受影响
- 测试注意：确认 `InputGuardrailTripwireTriggered` 和 `OutputGuardrailTripwireTriggered` 是 openai-agents SDK 中的正确异常类名，如果 SDK 版本不同可能需要调整 import 路径

---

## P1-2: BM25 索引持久化与标题元数据缓存

### 背景

当前存在两个性能问题：
1. `BM25Retriever.__init__` 每次实例化都扫描磁盘、读取所有文件、jieba 分词、构建 BM25 索引。文档增多后启动慢且查询时如果重建也会慢
2. `_search_based_title` 每次查询都调用 `MarkDownUtils.collect_md_metadata` 扫描磁盘目录

### 设计方案

1. **BM25 索引序列化**：构建完成后用 pickle 保存到磁盘，下次启动时优先加载序列化文件，仅在文件变更时重建
2. **标题元数据 MySQL 表**：文档入库时将标题、路径、摘要等元信息写入 MySQL `document_metadata` 表，查询时从数据库读取而非扫描磁盘

### 实现步骤 — BM25 持久化

**文件**: `backend/knowledge/services/bm25_retriever.py`，重写为：

```python
import os
import pickle
import hashlib
import logging
import jieba
from pathlib import Path
from typing import List
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from config.settings import settings

SUPPORTED_EXTENSIONS = {'.md', '.txt', '.docx', '.pdf'}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 索引文件存储路径
BM25_INDEX_PATH = os.path.join(settings._project_root, "data", "bm25_index.pkl")
BM25_HASH_PATH = os.path.join(settings._project_root, "data", "bm25_hash.txt")


class BM25Retriever:
    """
    BM25 keyword-based retriever with persistent index.
    Index is rebuilt only when document files change (based on directory hash).
    """

    def __init__(self):
        self.corpus_texts: List[str] = []
        self.corpus_paths: List[str] = []
        self.corpus_titles: List[str] = []
        self.bm25: BM25Okapi | None = None

        current_hash = self._compute_directory_hash()
        if self._try_load_index(current_hash):
            logger.info("BM25 index loaded from disk cache")
        else:
            self._build_index()
            self._save_index(current_hash)

    def _compute_directory_hash(self) -> str:
        """
        计算文档目录的指纹：基于所有文件名 + 文件大小 + 修改时间。
        任何文件的增删改都会导致 hash 变化，从而触发索引重建。
        """
        hasher = hashlib.md5()
        dirs_to_scan = [
            settings.CRAWL_OUTPUT_DIR,
            os.path.join(settings._project_root, "data", "uploaded"),
        ]
        for scan_dir in sorted(dirs_to_scan):
            if not os.path.exists(scan_dir):
                continue
            for fname in sorted(os.listdir(scan_dir)):
                if Path(fname).suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                fpath = os.path.join(scan_dir, fname)
                stat = os.stat(fpath)
                hasher.update(f"{fpath}:{stat.st_size}:{stat.st_mtime}".encode())
        return hasher.hexdigest()

    def _try_load_index(self, current_hash: str) -> bool:
        """尝试从磁盘加载已有索引，如果 hash 一致则加载成功。"""
        if not os.path.exists(BM25_INDEX_PATH) or not os.path.exists(BM25_HASH_PATH):
            return False
        try:
            with open(BM25_HASH_PATH, "r") as f:
                saved_hash = f.read().strip()
            if saved_hash != current_hash:
                logger.info("Document files changed, will rebuild BM25 index")
                return False
            with open(BM25_INDEX_PATH, "rb") as f:
                data = pickle.load(f)
            self.corpus_texts = data["corpus_texts"]
            self.corpus_paths = data["corpus_paths"]
            self.corpus_titles = data["corpus_titles"]
            self.bm25 = data["bm25"]
            return True
        except Exception as e:
            logger.warning(f"Failed to load BM25 index: {e}")
            return False

    def _save_index(self, current_hash: str):
        """将构建完成的索引序列化到磁盘。"""
        try:
            os.makedirs(os.path.dirname(BM25_INDEX_PATH), exist_ok=True)
            data = {
                "corpus_texts": self.corpus_texts,
                "corpus_paths": self.corpus_paths,
                "corpus_titles": self.corpus_titles,
                "bm25": self.bm25,
            }
            with open(BM25_INDEX_PATH, "wb") as f:
                pickle.dump(data, f)
            with open(BM25_HASH_PATH, "w") as f:
                f.write(current_hash)
            logger.info(f"BM25 index saved to {BM25_INDEX_PATH}")
        except Exception as e:
            logger.warning(f"Failed to save BM25 index: {e}")

    def rebuild_index(self):
        """公开方法：强制重建索引（文档上传后调用）。"""
        self.corpus_texts.clear()
        self.corpus_paths.clear()
        self.corpus_titles.clear()
        self.bm25 = None
        self._build_index()
        self._save_index(self._compute_directory_hash())

    def _read_file_content(self, file_path: str) -> str:
        """根据文件格式读取内容。"""
        ext = Path(file_path).suffix.lower()
        if ext in ('.md', '.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        elif ext in ('.pdf', '.docx'):
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(file_path)
            return result.document.export_to_markdown().strip()
        return ""

    def _build_index(self):
        """从磁盘文件构建 BM25 索引。"""
        dirs_to_scan = [
            settings.CRAWL_OUTPUT_DIR,
            os.path.join(settings._project_root, "data", "uploaded"),
        ]
        tokenized_corpus = []
        for scan_dir in dirs_to_scan:
            if not os.path.exists(scan_dir):
                continue
            files = [f for f in os.listdir(scan_dir)
                     if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS]
            for file_name in files:
                file_path = os.path.join(scan_dir, file_name)
                try:
                    content = self._read_file_content(file_path)
                    if not content:
                        continue
                    title = os.path.splitext(file_name)[0]
                    if '-' in title:
                        title = title.split('-', 1)[1]
                    self.corpus_texts.append(content)
                    self.corpus_paths.append(file_path)
                    self.corpus_titles.append(title)
                    tokens = list(jieba.cut(content))
                    tokenized_corpus.append(tokens)
                except Exception as e:
                    logger.error(f"Failed to read {file_path}: {e}")
                    continue

        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)
            logger.info(f"BM25 index built with {len(tokenized_corpus)} documents")
        else:
            logger.warning("BM25 index is empty - no documents loaded")

    def search(self, query: str, top_k: int = 10) -> List[Document]:
        """BM25 检索，与原逻辑完全相同。"""
        if self.bm25 is None or not self.corpus_texts:
            return []
        tokenized_query = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        documents = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            doc = Document(
                page_content=self.corpus_texts[idx],
                metadata={
                    "path": self.corpus_paths[idx],
                    "title": self.corpus_titles[idx],
                    "bm25_score": float(scores[idx]),
                }
            )
            documents.append(doc)
        logger.info(f"BM25 retrieved {len(documents)} documents for query: {query[:30]}...")
        return documents
```

### 实现步骤 — 文档上传后触发索引重建

**文件**: `backend/knowledge/api/routers.py`

在 `upload_file` 函数的成功返回之前，触发 BM25 索引重建：

```python
# 在 "6. 更新状态：已索引" 之后、return 之前，添加：
try:
    retrieval_service.bm25_retriever.rebuild_index()
except Exception as e:
    logger.warning(f"BM25 索引重建失败（不影响上传）: {e}")
```

### 实现步骤 — 标题元数据缓存

**方案**: 在 `RetrievalService` 中为 `_search_based_title` 添加内存缓存，避免每次查询都扫描磁盘。

**文件**: `backend/knowledge/services/retrieval_service.py`

在 `RetrievalService.__init__` 中添加缓存字段：

```python
def __init__(self):
    self.chroma_vector = VectorStoreRepository()
    self.spliter = IngestionProcessor()
    self._hyde_service = None
    self._bm25_retriever = None
    self._reranker_service = None
    # 新增：标题元数据缓存
    self._title_metadata_cache = None
    self._title_cache_hash = None
```

修改 `_search_based_title` 方法，添加缓存逻辑：

```python
def _search_based_title(self, user_query: str) -> List[Document]:
    """Title-based retrieval with caching."""
    mds_metadata = self._get_cached_title_metadata()
    # ... 后续逻辑不变
```

新增缓存方法：

```python
def _get_cached_title_metadata(self):
    """获取标题元数据，优先从缓存读取。"""
    import hashlib
    # 计算目录指纹
    current_hash = self._compute_dir_hash(settings.CRAWL_OUTPUT_DIR)
    if self._title_metadata_cache is not None and self._title_cache_hash == current_hash:
        return [dict(m) for m in self._title_metadata_cache]  # 返回副本
    # 缓存未命中，重新加载
    self._title_metadata_cache = MarkDownUtils.collect_md_metadata(settings.CRAWL_OUTPUT_DIR)
    self._title_cache_hash = current_hash
    logger.info(f"Title metadata cache refreshed: {len(self._title_metadata_cache)} entries")
    return [dict(m) for m in self._title_metadata_cache]

def _compute_dir_hash(self, dir_path: str) -> str:
    import hashlib
    hasher = hashlib.md5()
    if not os.path.exists(dir_path):
        return ""
    for fname in sorted(os.listdir(dir_path)):
        fpath = os.path.join(dir_path, fname)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            hasher.update(f"{fname}:{stat.st_size}:{stat.st_mtime}".encode())
    return hasher.hexdigest()
```

需要在文件顶部添加 `import os`。

### 验证

- 首次启动知识库服务 → 控制台打印 "BM25 index built with X documents" + "BM25 index saved to ..."
- 第二次启动（文档无变化）→ 打印 "BM25 index loaded from disk cache"，启动速度明显加快
- 上传新文档 → 打印 "BM25 索引重建"
- 连续两次相同查询 → 第二次标题检索走缓存，不打印 "Title metadata cache refreshed"

---

## P1-3: 售后 Agent 对接 MySQL 真实数据

### 背景

当前 `backend/app/infrastructure/tools/local/after_sales.py` 中三个工具全部使用硬编码的 Mock 字典，与企业级项目差距明显。

### 设计方案

1. 创建三张 MySQL 表：`orders`、`warranty_records`、`repair_tickets`
2. 提供初始化脚本插入示例数据
3. 重写三个工具函数，从 MySQL 查询

### 新建表初始化

**文件**: `backend/app/repositories/after_sales_repository.py`（新建）

```python
from infrastructure.database.database_pool import DatabasePool
from infrastructure.logging.logger import logger
from pymysql.cursors import DictCursor


def _get_conn():
    return DatabasePool.get_connection()


def init_after_sales_tables():
    """创建售后相关的三张表。"""
    conn = _get_conn()
    try:
        cursor = conn.cursor()

        # 订单表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                order_id VARCHAR(32) UNIQUE NOT NULL COMMENT '订单编号',
                user_id INT NULL COMMENT '关联用户ID',
                product VARCHAR(128) NOT NULL COMMENT '商品名称',
                status VARCHAR(64) NOT NULL COMMENT '订单状态',
                logistics VARCHAR(128) NULL COMMENT '物流信息',
                estimated_delivery VARCHAR(64) NULL COMMENT '预计送达',
                purchase_date DATE NOT NULL COMMENT '下单日期',
                amount DECIMAL(10,2) NULL COMMENT '订单金额',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_order_id (order_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # 保修记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS warranty_records (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                product VARCHAR(128) NOT NULL COMMENT '产品型号',
                serial_number VARCHAR(64) NULL COMMENT '序列号',
                purchase_date DATE NOT NULL COMMENT '购买日期',
                warranty_end DATE NOT NULL COMMENT '保修到期',
                warranty_type VARCHAR(128) NOT NULL COMMENT '保修类型',
                status VARCHAR(32) NOT NULL COMMENT '保修状态',
                user_id INT NULL COMMENT '关联用户ID',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_product (product),
                INDEX idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # 维修工单表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repair_tickets (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                repair_id VARCHAR(32) UNIQUE NOT NULL COMMENT '工单编号',
                product VARCHAR(128) NOT NULL COMMENT '设备型号',
                issue TEXT NOT NULL COMMENT '故障描述',
                status VARCHAR(64) NOT NULL COMMENT '维修状态',
                received_date DATE NOT NULL COMMENT '送修日期',
                estimated_completion DATE NULL COMMENT '预计完成',
                technician_note TEXT NULL COMMENT '工程师备注',
                user_id INT NULL COMMENT '关联用户ID',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_repair_id (repair_id),
                INDEX idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        conn.commit()
        logger.info("After-sales tables initialized (orders, warranty_records, repair_tickets)")
    except Exception as e:
        logger.error(f"Failed to create after-sales tables: {e}")
        raise
    finally:
        conn.close()


def query_order_by_id(order_id: str) -> dict | None:
    conn = _get_conn()
    try:
        cursor = conn.cursor(DictCursor)
        cursor.execute(
            "SELECT order_id, product, status, logistics, estimated_delivery, purchase_date, amount "
            "FROM orders WHERE order_id = %s",
            (order_id.upper(),)
        )
        return cursor.fetchone()
    finally:
        conn.close()


def query_warranty_by_product(product: str) -> dict | None:
    conn = _get_conn()
    try:
        cursor = conn.cursor(DictCursor)
        cursor.execute(
            "SELECT product, purchase_date, warranty_end, warranty_type, status "
            "FROM warranty_records WHERE product LIKE %s ORDER BY purchase_date DESC LIMIT 1",
            (f"%{product}%",)
        )
        return cursor.fetchone()
    finally:
        conn.close()


def query_repair_by_id(repair_id: str) -> dict | None:
    conn = _get_conn()
    try:
        cursor = conn.cursor(DictCursor)
        cursor.execute(
            "SELECT repair_id, product, issue, status, received_date, estimated_completion, technician_note "
            "FROM repair_tickets WHERE repair_id = %s",
            (repair_id.upper(),)
        )
        return cursor.fetchone()
    finally:
        conn.close()
```

### 初始化脚本

**文件**: `backend/app/scripts/init_after_sales_data.py`（新建）

```python
"""
初始化售后相关的示例数据。
运行方式: cd backend/app && python scripts/init_after_sales_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database.database_pool import DatabasePool


def seed_data():
    conn = DatabasePool.get_connection()
    try:
        cursor = conn.cursor()

        # 订单数据
        cursor.execute("SELECT COUNT(*) FROM orders")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO orders (order_id, product, status, logistics, estimated_delivery, purchase_date, amount) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    ("ORD20240512001", "ThinkPad X1 Carbon Gen 11", "已发货，运输中", "顺丰快递 SF1234567890", "2024年5月15日", "2024-05-12", 9999.00),
                    ("ORD20240510002", "ThinkPad T14s Gen 4", "已签收", "京东物流 JD0987654321", "已送达", "2024-05-10", 7499.00),
                    ("ORD20240508003", "Legion Y9000P 2024", "仓库处理中", "待发货", "预计2024年5月18日发货", "2024-05-08", 8999.00),
                    ("ORD20240601004", "小米14 Pro", "已签收", "中通快递 ZTO1122334455", "已送达", "2024-06-01", 4999.00),
                    ("ORD20240615005", "华为MatePad Pro 13.2", "已发货，运输中", "韵达快递 YD5566778899", "2024年6月18日", "2024-06-15", 5699.00),
                ]
            )
            print("订单数据已插入")

        # 保修数据
        cursor.execute("SELECT COUNT(*) FROM warranty_records")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO warranty_records (product, purchase_date, warranty_end, warranty_type, status) "
                "VALUES (%s, %s, %s, %s, %s)",
                [
                    ("ThinkPad X1 Carbon Gen 11", "2024-01-10", "2027-01-10", "整机1年 + 主要部件延保至3年", "在保修期内"),
                    ("ThinkPad T14s Gen 4", "2023-06-15", "2024-06-15", "整机1年", "已过保"),
                    ("Legion Y9000P 2024", "2024-03-20", "2027-03-20", "整机1年 + 主要部件延保至3年", "在保修期内"),
                    ("小米14 Pro", "2024-06-01", "2025-06-01", "整机1年", "在保修期内"),
                    ("华为MatePad Pro 13.2", "2024-06-15", "2025-06-15", "整机1年", "在保修期内"),
                ]
            )
            print("保修数据已插入")

        # 维修工单数据
        cursor.execute("SELECT COUNT(*) FROM repair_tickets")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO repair_tickets (repair_id, product, issue, status, received_date, estimated_completion, technician_note) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    ("RPR20240501", "ThinkPad X1 Carbon Gen 11", "屏幕显示异常，出现彩色条纹", "维修中", "2024-05-01", "2024-05-16", "已确认为屏幕排线故障，配件已到，预计2个工作日完成"),
                    ("RPR20240428", "Legion Y9000P 2024", "键盘部分按键失灵", "待取机", "2024-04-28", "2024-05-10", "已更换键盘模块，测试正常，请携带取机凭证到店取机"),
                    ("RPR20240505", "ThinkPad T14s Gen 4", "电池无法充电", "已接单，等待检测", "2024-05-05", "2024-05-20", "设备已收到，排队等待工程师检测"),
                    ("RPR20240610", "小米14 Pro", "屏幕碎裂", "维修中", "2024-06-10", "2024-06-17", "屏幕总成已到货，更换中"),
                ]
            )
            print("维修工单数据已插入")

        conn.commit()
        print("所有售后数据初始化完成")
    finally:
        conn.close()


if __name__ == "__main__":
    from repositories.after_sales_repository import init_after_sales_tables
    init_after_sales_tables()
    seed_data()
```

### 重写工具函数

**文件**: `backend/app/infrastructure/tools/local/after_sales.py`，完全重写为：

```python
from agents import function_tool
from infrastructure.logging.logger import logger
from repositories.after_sales_repository import (
    query_order_by_id,
    query_warranty_by_product,
    query_repair_by_id,
)


@function_tool
async def query_order_status(order_id: str) -> str:
    """
    查询订单状态和物流信息。

    Args:
        order_id: 订单编号，如 ORD20240512001

    Returns:
        订单状态信息，包含商品名称、物流状态、预计送达时间
    """
    logger.info(f"[AfterSales] 查询订单状态: {order_id}")
    order = query_order_by_id(order_id)
    if order:
        return (
            f"订单 {order['order_id']} 状态：\n"
            f"- 商品：{order['product']}\n"
            f"- 状态：{order['status']}\n"
            f"- 物流：{order['logistics']}\n"
            f"- 预计送达：{order['estimated_delivery']}\n"
            f"- 下单日期：{order['purchase_date']}"
        )
    return f"未找到订单号 {order_id}，请确认订单号是否正确。订单号格式通常为 ORD 开头，如 ORD20240512001。"


@function_tool
async def query_warranty_info(product: str) -> str:
    """
    查询产品的保修信息和保修状态。

    Args:
        product: 产品名称或型号，如 ThinkPad X1 Carbon

    Returns:
        保修信息，包含购买日期、保修到期日、保修类型、当前状态
    """
    logger.info(f"[AfterSales] 查询保修信息: {product}")
    warranty = query_warranty_by_product(product)
    if warranty:
        return (
            f"{warranty['product']} 保修信息：\n"
            f"- 购买日期：{warranty['purchase_date']}\n"
            f"- 保修到期：{warranty['warranty_end']}\n"
            f"- 保修类型：{warranty['warranty_type']}\n"
            f"- 当前状态：{warranty['status']}"
        )
    return f"未找到产品「{product}」的保修信息，请确认产品型号是否正确。"


@function_tool
async def query_repair_progress(repair_id: str) -> str:
    """
    查询维修工单的进度和状态。

    Args:
        repair_id: 维修工单号，如 RPR20240501

    Returns:
        维修进度信息，包含设备型号、故障描述、当前状态、预计完成时间、工程师备注
    """
    logger.info(f"[AfterSales] 查询维修进度: {repair_id}")
    repair = query_repair_by_id(repair_id)
    if repair:
        return (
            f"维修工单 {repair['repair_id']} 进度：\n"
            f"- 设备：{repair['product']}\n"
            f"- 故障：{repair['issue']}\n"
            f"- 当前状态：{repair['status']}\n"
            f"- 送修日期：{repair['received_date']}\n"
            f"- 预计完成：{repair['estimated_completion']}\n"
            f"- 工程师备注：{repair['technician_note']}"
        )
    return f"未找到维修工单 {repair_id}，请确认工单号是否正确。工单号格式通常为 RPR 开头，如 RPR20240501。"
```

### 注册表初始化

**文件**: `backend/app/api/main.py`

在 `lifespan` 函数中已有的表初始化块之后，添加：

```python
try:
    from repositories.after_sales_repository import init_after_sales_tables
    init_after_sales_tables()
    logger.info("售后相关表初始化完成")
except Exception as e:
    logger.error(f"售后相关表初始化失败: {str(e)}")
```

### 验证

- 运行初始化脚本：`cd backend/app && python scripts/init_after_sales_data.py`
- 通过 Agent 查询："订单号 ORD20240512001 到哪了？" → 应从 MySQL 返回数据
- 查询不存在的订单号 → 应返回未找到提示
- 查询保修："ThinkPad X1 Carbon 还在保修期内吗？" → 应返回保修信息

---

## P1-4: 对话上下文智能压缩

### 背景

当前 `conversation_service.py` 的 `_truncate_history` 简单截断最近 3 轮（6 条消息），导致早期重要信息（如用户说的设备型号、问题背景）丢失。

### 设计方案

用 LLM 将超出窗口的历史对话压缩为一段摘要，注入为 system 消息。保留最近 N 轮原始消息 + 之前所有对话的摘要。

### 新建文件

**文件**: `backend/app/services/context_compressor.py`（新建）

```python
"""
对话上下文压缩服务。
将超出滑动窗口的历史消息用 LLM 压缩为摘要。
"""

from typing import List, Dict, Any
from infrastructure.ai.openai_client import sub_model_client
from config.settings import settings
from infrastructure.logging.logger import logger


SUMMARY_PROMPT = """请用中文将以下对话历史压缩为一段简洁的摘要（不超过200字）。
重点保留：
1. 用户提到的设备型号、品牌
2. 用户遇到的具体问题和诉求
3. 系统已给出的关键建议或操作结果
4. 任何重要的上下文信息（如位置、订单号、工单号）

不要保留寒暄、重复内容或系统内部的工具调用细节。

对话历史：
{conversation}

摘要："""


async def compress_history(
    messages: List[Dict[str, Any]],
    keep_recent: int = 3,
) -> List[Dict[str, Any]]:
    """
    压缩对话历史：保留最近 keep_recent 轮 + 将更早的对话压缩为摘要。

    Args:
        messages: 完整对话历史（不含 system 消息）
        keep_recent: 保留的最近轮数（1轮=1对 user+assistant）

    Returns:
        压缩后的消息列表，格式为 [system_summary, ...recent_messages]
    """
    msg_limit = keep_recent * 2
    if len(messages) <= msg_limit:
        return messages

    # 分割：需要压缩的旧消息 vs 保留的近期消息
    old_messages = messages[:-msg_limit]
    recent_messages = messages[-msg_limit:]

    # 构建对话文本
    conversation_text = "\n".join(
        f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:300]}"
        for m in old_messages
    )

    try:
        response = await sub_model_client.chat.completions.create(
            model=settings.SUB_MODEL_NAME,
            messages=[{"role": "user", "content": SUMMARY_PROMPT.format(conversation=conversation_text)}],
            temperature=0,
            max_tokens=300,
        )
        summary = response.choices[0].message.content.strip()
        logger.info(f"对话摘要生成成功: {len(summary)} 字符")
    except Exception as e:
        logger.warning(f"对话摘要生成失败，回退到简单截断: {e}")
        return recent_messages

    # 将摘要作为 system 消息注入
    summary_message = {
        "role": "system",
        "content": f"以下是之前对话的摘要，供你理解用户上下文：\n{summary}"
    }

    return [summary_message] + recent_messages
```

### 修改 conversation_service.py

**文件**: `backend/app/services/conversation_service.py`

替换 `prepare_history` 方法中的截断逻辑：

```python
# 原来的 prepare_history 方法（同步）改为异步
async def prepare_history(self, user_id: int, username: str, session_id: str | None, user_input: str, max_turn: int = 3) -> List[Dict[str, Any]]:
    target_session_id = session_id if session_id else self.DEFAULT_SESSION_ID
    session_pk = self._session_repo.get_or_create_session(user_id, target_session_id)

    self._message_repo.append_message(session_pk, "user", user_input)

    messages = self._message_repo.get_messages_by_session(session_pk)
    chat_history = [{"role": row[0], "content": row[1]} for row in messages]

    # 分离 system 消息
    system_msgs = [m for m in chat_history if m.get("role") == "system"]
    non_system_msgs = [m for m in chat_history if m.get("role") != "system"]

    # 使用智能压缩替代简单截断
    from services.context_compressor import compress_history
    compressed = await compress_history(non_system_msgs, keep_recent=max_turn)

    return system_msgs + compressed
```

### 修改 agent_service.py

由于 `prepare_history` 变为异步方法，需要在调用处添加 `await`：

**文件**: `backend/app/services/agent_service.py`，约第 44 行：

```python
# 原来：
chat_history = conversation_service.prepare_history(numeric_id, username, session_id, user_query)
# 改为：
chat_history = await conversation_service.prepare_history(numeric_id, username, session_id, user_query)
```

### 验证

- 在同一会话中发送 5 轮以上消息
- 第 6 轮发送时，检查后端日志应出现 "对话摘要生成成功"
- 第 6 轮引用第 1 轮提到的信息（如 "我之前说的那台电脑"），Agent 应能正确理解

---

## P2-1: Markdown 语义分块

### 背景

当前使用 `RecursiveCharacterTextSplitter`（chunk_size=1500），纯字符级切分不考虑文档语义结构。对 Markdown 文档，按标题层级切分能保持每块的语义完整性。

### 实现步骤

**文件**: `backend/knowledge/services/ingestion/ingestion_processor.py`

修改 `__init__` 和 `ingest_file`：

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

class IngestionProcessor:
    def __init__(self):
        self.vector_store = VectorStoreRepository()

        # Markdown 语义分块器：按标题层级切分
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "h1"),
                ("##", "h2"),
                ("###", "h3"),
            ],
            strip_headers=False,  # 保留标题文本在块内容中
        )

        # 二级分块器：对语义分块后仍过长的块做字符级切分
        self.document_spliter = RecursiveCharacterTextSplitter(
            chunk_size=1000,        # 从 1500 降低到 1000
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
```

修改 `ingest_file` 方法中第 3 步的切分逻辑：

```python
# 3. 切分文档（语义分块 + 二级字符分块）
final_document_chunks = []
for doc in documents:
    ext = Path(file_path).suffix.lower()
    content = doc.page_content
    title = doc.metadata.get('title', '')

    if ext == '.md' and len(content) >= 500:
        # Markdown 文件：先按标题语义切分
        md_chunks = self.markdown_splitter.split_text(content)
        for md_chunk in md_chunks:
            chunk_text = md_chunk.page_content
            chunk_metadata = {**doc.metadata, **md_chunk.metadata}
            if len(chunk_text) > 1200:
                # 语义块太长，再做字符级切分
                sub_chunks = self.document_spliter.split_text(chunk_text)
                for i, sub in enumerate(sub_chunks):
                    sub_doc = Document(
                        page_content=f"文档来源:{title}\n{sub}",
                        metadata={**chunk_metadata, "chunk_index": i}
                    )
                    final_document_chunks.append(sub_doc)
            else:
                final_document_chunks.append(Document(
                    page_content=f"文档来源:{title}\n{chunk_text}",
                    metadata=chunk_metadata
                ))
    elif len(content) < 1200:
        # 短文档不切分
        final_document_chunks.append(doc)
    else:
        # 非 Markdown 或无标题结构的长文档：字符级切分
        chunks = self.document_spliter.split_documents([doc])
        for chunk in chunks:
            chunk.page_content = f"文档来源:{title}\n{chunk.page_content}"
        final_document_chunks.extend(chunks)
```

### 验证

- 上传一个多级标题的 Markdown 文件
- 检查 ChromaDB 中的块数量和内容，确认每块对应一个标题章节
- 对比改进前后的检索质量：用相同问题查询，比较返回的上下文相关性

---

## P2-2: RAG 查询路由器

### 背景

当前所有查询都走完整管线（HyDE → 三路检索 → 重排）。简单关键词查询不需要 HyDE，复杂多跳查询可能需要分解为子查询。

### 新建文件

**文件**: `backend/knowledge/services/query_router.py`（新建）

```python
"""
查询路由器：根据查询复杂度选择不同的检索策略。

策略：
- SIMPLE: 跳过 HyDE，直接三路检索 + 重排
- STANDARD: 完整管线（HyDE + 三路检索 + 重排）
- COMPLEX: 查询分解为子查询，分别检索后合并去重 + 重排
"""

import re
import logging
from enum import Enum
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryComplexity(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"


# 简单查询的特征：短查询、单一主题
SIMPLE_INDICATORS = [
    lambda q: len(q) < 15,                          # 短于 15 字符
    lambda q: "怎么" in q and len(q) < 25,           # 简单的 "怎么" 问题
    lambda q: q.count("？") <= 1 and len(q) < 30,    # 单个问号且短
]

# 复杂查询的特征：多个问题、条件、比较
COMPLEX_INDICATORS = [
    lambda q: q.count("？") >= 2,                     # 多个问号
    lambda q: bool(re.search(r"(如果|假如|假设).+(那么|就|则)", q)),  # 条件句
    lambda q: bool(re.search(r"(比较|对比|区别|不同)", q)),           # 比较
    lambda q: bool(re.search(r"(以及|并且|同时|还有).+\?", q)),      # 多个并列要求
    lambda q: len(q) > 80,                            # 长查询
]


def classify_query(query: str) -> QueryComplexity:
    """
    分类查询复杂度。

    Args:
        query: 用户查询

    Returns:
        QueryComplexity 枚举值
    """
    # 先检查是否复杂
    complex_score = sum(1 for fn in COMPLEX_INDICATORS if fn(query))
    if complex_score >= 2:
        logger.info(f"[QueryRouter] COMPLEX query: {query[:30]}...")
        return QueryComplexity.COMPLEX

    # 再检查是否简单
    simple_score = sum(1 for fn in SIMPLE_INDICATORS if fn(query))
    if simple_score >= 1:
        logger.info(f"[QueryRouter] SIMPLE query: {query[:30]}...")
        return QueryComplexity.SIMPLE

    logger.info(f"[QueryRouter] STANDARD query: {query[:30]}...")
    return QueryComplexity.STANDARD


def decompose_query(query: str) -> List[str]:
    """
    将复杂查询分解为多个子查询（基于规则）。
    返回子查询列表，至少包含原始查询。
    """
    sub_queries = [query]

    # 按中文问号拆分
    if "？" in query:
        parts = [p.strip() for p in query.split("？") if p.strip()]
        if len(parts) > 1:
            sub_queries = [p + "？" if not p.endswith("？") else p for p in parts]

    # 按 "以及"/"并且"/"同时" 拆分
    elif re.search(r"(以及|并且|同时|还有)", query):
        parts = re.split(r"(?:以及|并且|同时|还有)", query)
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 5]
        if len(parts) > 1:
            sub_queries = parts

    logger.info(f"[QueryRouter] Decomposed into {len(sub_queries)} sub-queries")
    return sub_queries
```

### 集成到 RetrievalService

**文件**: `backend/knowledge/services/retrieval_service.py`

修改 `retrieval` 方法：

```python
from services.query_router import classify_query, decompose_query, QueryComplexity

def retrieval(self, user_question: str) -> List[Document]:
    # 0. 查询路由
    complexity = classify_query(user_question)

    if complexity == QueryComplexity.SIMPLE:
        # 简单查询：跳过 HyDE
        return self._retrieval_simple(user_question)
    elif complexity == QueryComplexity.COMPLEX:
        # 复杂查询：分解 + 多次检索 + 合并
        return self._retrieval_complex(user_question)
    else:
        # 标准查询：完整管线
        return self._retrieval_standard(user_question)

def _retrieval_simple(self, user_question: str) -> List[Document]:
    """简单查询：跳过 HyDE，直接检索。"""
    bm25_candidates = self._search_bm25(user_question)
    vector_candidates = self._search_based_vector(user_question)  # 直接用原始 query
    title_candidates = self._search_based_title(user_question)
    all_candidates = bm25_candidates + vector_candidates + title_candidates
    unique_candidates = self._deduplicate(all_candidates)
    if not unique_candidates:
        return []
    if settings.RERANKER_ENABLED:
        return self.reranker_service.rerank(user_question, unique_candidates)
    return self._cosine_rerank(user_question, unique_candidates)

def _retrieval_standard(self, user_question: str) -> List[Document]:
    """标准查询：完整 HyDE + 三路检索 + 重排（原有逻辑）。"""
    if settings.HYDE_ENABLED:
        search_query = self.hyde_service.generate_hypothetical_document(user_question)
    else:
        search_query = user_question
    bm25_candidates = self._search_bm25(user_question)
    vector_candidates = self._search_based_vector(search_query)
    title_candidates = self._search_based_title(user_question)
    all_candidates = bm25_candidates + vector_candidates + title_candidates
    unique_candidates = self._deduplicate(all_candidates)
    if not unique_candidates:
        return []
    if settings.RERANKER_ENABLED:
        return self.reranker_service.rerank(user_question, unique_candidates)
    return self._cosine_rerank(user_question, unique_candidates)

def _retrieval_complex(self, user_question: str) -> List[Document]:
    """复杂查询：分解为子查询，分别检索后合并。"""
    sub_queries = decompose_query(user_question)
    all_candidates = []
    for sub_q in sub_queries:
        bm25_candidates = self._search_bm25(sub_q)
        vector_candidates = self._search_based_vector(sub_q)
        all_candidates.extend(bm25_candidates + vector_candidates)
    # 标题检索只用原始查询
    title_candidates = self._search_based_title(user_question)
    all_candidates.extend(title_candidates)
    unique_candidates = self._deduplicate(all_candidates)
    if not unique_candidates:
        return []
    if settings.RERANKER_ENABLED:
        return self.reranker_service.rerank(user_question, unique_candidates)
    return self._cosine_rerank(user_question, unique_candidates)
```

### 验证

- 短查询 "WiFi密码" → 日志显示 SIMPLE，跳过 HyDE
- 正常查询 "电脑开机蓝屏如何处理" → 日志显示 STANDARD
- 复杂查询 "电脑蓝屏怎么办？以及如何备份重要数据？" → 日志显示 COMPLEX，分解为 2 个子查询

---

## P2-3: Agent 结构化输出

### 背景

当前工具返回纯文本字符串，前端无法做差异化渲染。希望关键工具返回结构化 JSON，前端可以渲染为卡片。

### 设计方案

1. 定义新的 SSE 消息类型 `STRUCTURED`，携带结构化数据
2. 售后工具和服务站工具返回 JSON，标记类型
3. 前端识别 `STRUCTURED` 类型并渲染卡片

### 新增 Schema

**文件**: `backend/app/schemas/response.py`

在 `ContentKind` 枚举中添加：

```python
class ContentKind(str, Enum):
    THINKING = 'THINKING'
    PROCESS = 'PROCESS'
    ANSWER = 'ANSWER'
    STRUCTURED = 'STRUCTURED'   # 新增：结构化数据
```

新增结构化消息体：

```python
class StructuredMessageBody(MessageBody):
    """
    结构化消息体：承载可被前端渲染为卡片的数据。
    """
    contentType: Literal['sagegpt/structured'] = 'sagegpt/structured'
    kind: ContentKind = ContentKind.STRUCTURED
    card_type: str = Field(..., description="卡片类型：order_status / warranty_info / repair_progress / service_station")
    data: dict = Field(..., description="结构化数据")
```

修改 `StreamPacket` 的 `content` 类型：

```python
class StreamPacket(BaseModel):
    id: str
    content: Union[TextMessageBody, FinishMessageBody, StructuredMessageBody]
    status: StreamStatus
    metadata: PacketMeta
```

### 修改 ResponseFactory

**文件**: `backend/app/utils/response_util.py`

新增构建方法：

```python
from schemas.response import StructuredMessageBody

@staticmethod
def build_structured(card_type: str, data: dict) -> StreamPacket:
    """构建结构化数据响应"""
    body = StructuredMessageBody(
        card_type=card_type,
        data=data
    )
    return StreamPacket(
        id=str(uuid.uuid4()),
        content=body,
        status=StreamStatus.IN_PROGRESS,
        metadata=PacketMeta(createTime=str(datetime.now()))
    )
```

### 前端处理

**文件**: `front/agent_web_ui/src/stores/chat.js`

在 `processSSEData` 函数中添加对 STRUCTURED 类型的处理：

```javascript
if (kind === 'ANSWER') appendAnswer(text)
else if (kind === 'THINKING') appendThinking(text)
else if (kind === 'STRUCTURED') {
  // 结构化数据：作为特殊消息类型存储
  chatMessages.value.push({
    type: 'STRUCTURED',
    cardType: parsed.content.card_type,
    data: parsed.content.data
  })
  chatMessages.value = [...chatMessages.value]
  scrollToBottom()
}
else appendThinking(text + '\n')
```

前端需要在 `ChatMessage.vue` 中添加对 `STRUCTURED` 类型消息的渲染组件（具体 UI 设计留给前端开发者决定，此处仅定义数据协议）。

### 验证

- 这是一个渐进式改进，初始阶段可以先定义 schema 和协议
- 后续逐个工具改造为返回结构化数据

---

## P2-4: API 限流

### 背景

当前没有任何速率限制，存在被滥用的风险。

### 实现步骤

1. 安装依赖：在 `backend/app/requirements.txt` 中添加 `slowapi`

2. **文件**: `backend/app/api/main.py`

在 `create_fast_api` 中添加限流配置：

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

def create_fast_api() -> FastAPI:
    app = FastAPI(title="ITS API", lifespan=lifespan)

    # 注册限流器
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ... 其余不变
```

3. **文件**: `backend/app/api/routers.py`

在 `/api/query` 路由上添加限流装饰器：

```python
from fastapi import Request
from api.main import limiter

@router.post("/api/query", summary="智能体对话接口")
@limiter.limit("10/minute")
async def query(request: Request, request_context: ChatMessageRequest, current_user: dict = Depends(get_current_user)) -> StreamingResponse:
    # ... 注意：添加 request: Request 参数（slowapi 需要）
```

**注意循环导入**：`routers.py` 从 `main.py` 导入 `limiter` 会导致循环导入。解决方案是将 `limiter` 移到独立模块：

**文件**: `backend/app/infrastructure/rate_limiter.py`（新建）

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

然后 `main.py` 和 `routers.py` 都从此模块导入。

### 验证

- 在 1 分钟内连续发送超过 10 次请求 → 应返回 429 Too Many Requests
- 正常频率使用不受影响

---

## P2-5: 健康检查端点

### 背景

部署时需要存活探针和就绪探针。

### 实现步骤

**文件**: `backend/app/api/routers.py`

添加健康检查路由：

```python
@router.get("/health", summary="健康检查")
async def health_check():
    """
    基础存活探针。
    检查 MySQL 连接池和 MCP 连接状态。
    """
    checks = {}

    # 1. MySQL
    try:
        from infrastructure.database.database_pool import DatabasePool
        conn = DatabasePool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        checks["mysql"] = "ok"
    except Exception as e:
        checks["mysql"] = f"error: {str(e)}"

    # 2. MCP 连接（轻量检查）
    try:
        from infrastructure.tools.mcp.mcp_servers import search_mcp_client, baidu_mcp_client
        checks["mcp_search"] = "connected"  # MCP 客户端在启动时连接
        checks["mcp_baidu"] = "connected"
    except Exception as e:
        checks["mcp"] = f"error: {str(e)}"

    all_ok = all(v == "ok" or v == "connected" for v in checks.values())

    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
    }
```

注意：此路由**不需要** `get_current_user` 依赖，允许匿名访问。

### 知识库服务也添加

**文件**: `backend/knowledge/api/routers.py`

```python
@router.get("/health", summary="知识库健康检查")
async def health_check():
    checks = {}
    try:
        from repositories.vector_store_repository import VectorStoreRepository
        vs = VectorStoreRepository()
        count = vs.vector_database._collection.count()
        checks["chromadb"] = f"ok ({count} vectors)"
    except Exception as e:
        checks["chromadb"] = f"error: {str(e)}"

    all_ok = all("ok" in v for v in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "checks": checks}
```

### 验证

- `curl http://127.0.0.1:8000/health` → 返回各组件状态
- `curl http://127.0.0.1:8001/health` → 返回 ChromaDB 状态
- MySQL 停掉后请求 → 返回 `"status": "degraded"`

---

## P2-6: 检索质量反馈闭环

### 背景

当前有 RAGAS 和 LLM-as-Judge 评测框架，但缺少在线用户反馈机制。

### 设计方案

1. 前端在每条 AI 回复下方添加 👍 / 👎 按钮
2. 点击后将反馈发送到后端 API
3. 后端存入 `feedback` 表，关联会话和消息
4. 可定期导出分析检索失败的 case

### 新建反馈表

**文件**: `backend/app/repositories/feedback_repository.py`（新建）

```python
from infrastructure.database.database_pool import DatabasePool
from infrastructure.logging.logger import logger


def _get_conn():
    return DatabasePool.get_connection()


def init_feedback_table():
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(128) NOT NULL,
                user_id INT NOT NULL,
                message_seq INT NULL COMMENT '关联的消息序号',
                rating TINYINT NOT NULL COMMENT '1=有用, -1=没用',
                comment TEXT NULL COMMENT '用户补充说明',
                user_query TEXT NULL COMMENT '触发此回复的用户问题',
                agent_answer TEXT NULL COMMENT 'Agent的回答（前500字符）',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session (session_id),
                INDEX idx_rating_created (rating, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        logger.info("user_feedback table initialized")
    except Exception as e:
        logger.error(f"Failed to create user_feedback table: {e}")
        raise
    finally:
        conn.close()


def insert_feedback(session_id: str, user_id: int, rating: int,
                    message_seq: int = None, comment: str = None,
                    user_query: str = None, agent_answer: str = None) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_feedback (session_id, user_id, message_seq, rating, comment, user_query, agent_answer) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (session_id, user_id, message_seq, rating, comment,
             user_query, agent_answer[:500] if agent_answer else None)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_negative_feedback(limit: int = 50, offset: int = 0) -> list:
    """获取差评反馈，用于分析检索质量问题。"""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_id, user_query, agent_answer, comment, created_at "
            "FROM user_feedback WHERE rating = -1 "
            "ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        return cursor.fetchall()
    finally:
        conn.close()
```

### 新增 API 路由

**文件**: `backend/app/api/routers.py`

添加反馈接口：

```python
from pydantic import BaseModel

class FeedbackRequest(BaseModel):
    session_id: str
    rating: int  # 1 或 -1
    message_seq: int | None = None
    comment: str | None = None
    user_query: str | None = None
    agent_answer: str | None = None


@router.post("/api/feedback", summary="用户反馈")
async def submit_feedback(request: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    """提交对 Agent 回答的反馈（有用/没用）。"""
    from repositories.feedback_repository import insert_feedback
    try:
        feedback_id = insert_feedback(
            session_id=request.session_id,
            user_id=current_user["user_id"],
            rating=request.rating,
            message_seq=request.message_seq,
            comment=request.comment,
            user_query=request.user_query,
            agent_answer=request.agent_answer,
        )
        return {"success": True, "feedback_id": feedback_id}
    except Exception as e:
        logger.error(f"反馈提交失败: {str(e)}")
        return {"success": False, "error": str(e)}
```

### 表初始化注册

**文件**: `backend/app/api/main.py`

在 `lifespan` 中添加：

```python
try:
    from repositories.feedback_repository import init_feedback_table
    init_feedback_table()
    logger.info("feedback表初始化完成")
except Exception as e:
    logger.error(f"feedback表初始化失败: {str(e)}")
```

### 前端（简要说明）

在 `ChatMessage.vue` 中，当消息类型为 `assistant` 时，在消息气泡下方渲染两个按钮：

```html
<div v-if="msg.type === 'assistant'" class="feedback-buttons">
  <button @click="submitFeedback(1)">👍 有用</button>
  <button @click="submitFeedback(-1)">👎 没用</button>
</div>
```

点击后调用 `authFetch('/api/feedback', ...)` 发送反馈。

### 验证

- 发送消息后点击 👍 → 数据写入 `user_feedback` 表
- 查询差评：`SELECT * FROM user_feedback WHERE rating = -1` → 可看到差评记录和对应的问题/回答

---

## 实施顺序总结

```
第 1 批（P0，立即可做，改动极小）:
  P0-1 → P0-2 → P0-3 → P0-4

第 2 批（P1，核心功能升级）:
  P1-3（售后MySQL）→ P1-1（Guardrails）→ P1-2（BM25持久化）→ P1-4（上下文压缩）

第 3 批（P2，体验与工程优化）:
  P2-5（健康检查）→ P2-4（限流）→ P2-1（语义分块）→ P2-2（查询路由）→ P2-6（反馈）→ P2-3（结构化输出）
```

每项完成后应：
1. 运行现有测试：`cd backend/app && pytest tests -m "not integration" -v`
2. 手动测试关键路径（发送消息、获取回复、会话管理）
3. 确认 CI 通过

---

## 附录：新建文件清单

| 文件路径 | 用途 |
|---------|------|
| `backend/app/multi_agent/guardrails.py` | Agent 输入/输出护栏 |
| `backend/app/services/context_compressor.py` | 对话上下文压缩 |
| `backend/app/repositories/after_sales_repository.py` | 售后数据 MySQL 操作 |
| `backend/app/scripts/init_after_sales_data.py` | 售后示例数据初始化脚本 |
| `backend/app/repositories/feedback_repository.py` | 用户反馈 MySQL 操作 |
| `backend/app/infrastructure/rate_limiter.py` | 限流器实例 |
| `backend/knowledge/services/query_router.py` | 查询复杂度分类与分解 |
| `front/agent_web_ui/.env` | 前端环境变量（开发） |
| `front/agent_web_ui/.env.production` | 前端环境变量（生产） |

## 附录：修改文件清单

| 文件路径 | 修改内容 |
|---------|---------|
| `backend/app/multi_agent/orchestrator_agent.py` | 改用 main_model + 添加 guardrails |
| `backend/app/multi_agent/agent_factory.py` | 移除 tracing_disabled |
| `backend/app/multi_agent/service_agent.py` | 移除全局 tracing 禁用 |
| `backend/app/services/agent_service.py` | 移除 tracing_disabled + 添加护栏异常处理 + await prepare_history |
| `backend/app/services/conversation_service.py` | prepare_history 改为异步 + 使用智能压缩 |
| `backend/app/config/settings.py` | 添加 JWT 密钥安全检查 + ENVIRONMENT 字段 |
| `backend/app/infrastructure/tools/local/after_sales.py` | 重写为 MySQL 查询 |
| `backend/app/api/main.py` | 注册新表初始化 + 限流 |
| `backend/app/api/routers.py` | 添加健康检查 + 反馈接口 + 限流装饰器 |
| `backend/app/schemas/response.py` | 添加 STRUCTURED 类型 |
| `backend/app/utils/response_util.py` | 添加 build_structured 方法 |
| `backend/app/requirements.txt` | 添加 slowapi 依赖 |
| `backend/knowledge/services/bm25_retriever.py` | 重写为持久化索引 |
| `backend/knowledge/services/retrieval_service.py` | 添加标题缓存 + 查询路由集成 |
| `backend/knowledge/services/ingestion/ingestion_processor.py` | 改为语义分块 |
| `backend/knowledge/api/routers.py` | 添加健康检查 + 上传后触发 BM25 重建 |
| `front/agent_web_ui/src/stores/chat.js` | 环境变量化 API_BASE + STRUCTURED 消息处理 |
| `front/agent_web_ui/src/stores/auth.js` | 环境变量化 API_BASE |
