# 执行升级计划的 Prompt

> 将以下 prompt 完整复制给执行模型（Claude / GPT / 其他）。  
> 根据需要替换 `[批次]` 部分来控制执行范围。

---

## Prompt 正文

```
你是一位高级后端工程师，负责对一个中文智能客服多智能体系统（ITS Multi-Agent）进行企业级升级改造。

## 你的任务

严格按照 `docs/UPGRADE_DESIGN.md` 设计文档，实现其中 [P0 全部 4 项 / P1 全部 4 项 / P2 全部 6 项 / 全部 14 项]（根据需要选择范围）升级改造。

## 工作规则

### 执行原则
1. **严格遵循设计文档**：`docs/UPGRADE_DESIGN.md` 是你的唯一实现依据。每一项的目标代码、文件路径、修改位置都已精确标注，不要偏离。
2. **按优先级顺序执行**：P0-1 → P0-2 → P0-3 → P0-4 → P1-1 → ... → P2-6。完成一项后再开始下一项。
3. **先读再改**：修改任何文件之前，先完整读取该文件的当前内容，确认行号和上下文与设计文档描述一致。如果实际代码与文档描述有出入，以实际代码为准来定位修改点，保持修改意图不变。
4. **最小化改动**：只做设计文档要求的修改，不要重构周边代码、不要添加额外功能、不要修改代码风格。
5. **保持现有功能不破坏**：改完每一项后，在心里检查是否引入了 import 循环、是否破坏了现有 API 签名、是否需要同步修改调用方。

### 代码规范
- 保持项目现有的中文注释风格（关键日志和错误信息用中文）
- 保持现有的 import 组织方式（标准库 → 三方库 → 项目内部）
- 不添加多余注释，只在有非显而易见的逻辑时加一行注释
- 新建文件时参照同目录下已有文件的格式和风格

### 新建文件
设计文档附录中列出了所有需要新建的文件。新建时：
- 确认父目录存在
- 文件内容直接取自设计文档中的完整代码块
- 如果代码块中有 `# ...` 省略标记，参照同项目已有代码补全

### 数据库表
- 新表通过 `init_xxx_table()` 函数在 `api/main.py` 的 `lifespan` 中注册，遵循项目现有模式
- 不使用 Alembic（项目当前不用 ORM）

### 依赖管理
- 如果某项需要新的 pip 包（如 slowapi），在 `backend/app/requirements.txt` 末尾追加
- 不要升级或修改已有依赖版本

### 验证
每完成一项后，运行以下检查（如果环境允许）：
```bash
cd backend/app && python -c "from config.settings import settings; print('settings OK')"
cd backend/app && python -c "from multi_agent.orchestrator_agent import orchestrator_agent; print('orchestrator OK')"
```
如果无法运行，至少检查所有被修改文件的 import 是否能解析。

## 项目上下文（供你理解，不要修改这些文件）

### 架构概要
- 两个后端服务：Main App（FastAPI :8000, 多智能体编排）+ Knowledge Service（FastAPI :8001, RAG 检索）
- 两个前端：agent_web_ui（Vue3 :5173, 聊天界面）+ knowlege_platform_ui（Vue3 :3000, 知识管理）
- Agent 框架：openai-agents SDK，Agent-as-Tool 模式
- 数据库：MySQL（pymysql + DBUtils 连接池），表通过 CREATE TABLE IF NOT EXISTS 自动建
- 配置：pydantic-settings 从 .env 加载

### 关键文件位置
- Agent 定义：`backend/app/multi_agent/` 下 4 个文件
- Agent 工具：`backend/app/infrastructure/tools/local/` 下 3 个文件
- MCP 客户端：`backend/app/infrastructure/tools/mcp/mcp_servers.py`
- LLM 客户端：`backend/app/infrastructure/ai/openai_client.py`（定义了 main_model 和 sub_model）
- 配置：`backend/app/config/settings.py`
- SSE 流处理：`backend/app/services/stream_response_service.py`
- 响应 Schema：`backend/app/schemas/response.py`
- 对话服务：`backend/app/services/conversation_service.py`
- 数据库连接池：`backend/app/infrastructure/database/database_pool.py`
- RAG 检索：`backend/knowledge/services/retrieval_service.py`
- BM25：`backend/knowledge/services/bm25_retriever.py`
- 文档入库：`backend/knowledge/services/ingestion/ingestion_processor.py`
- 前端状态管理：`front/agent_web_ui/src/stores/chat.js` 和 `auth.js`

## 开始执行

请先完整阅读 `docs/UPGRADE_DESIGN.md`，然后从第一项开始逐项实施。每完成一项，简要报告：
- 修改/新建了哪些文件
- 关键改动点
- 是否有与设计文档不一致的地方及如何处理

开始吧。
```

---

## 使用说明

### 按批次执行

如果希望分批次让模型执行，替换 prompt 中 `[P0 全部 4 项]` 部分：

| 批次 | 替换为 | 预计改动量 |
|------|--------|-----------|
| 第 1 批 | `P0 全部 4 项（P0-1 到 P0-4）` | 改 6 个文件，建 2 个文件 |
| 第 2 批 | `P1 全部 4 项（P1-1 到 P1-4）` | 改 6 个文件，建 4 个文件 |
| 第 3 批 | `P2 全部 6 项（P2-1 到 P2-6）` | 改 8 个文件，建 3 个文件 |
| 全量 | `全部 14 项` | 改 18 个文件，建 9 个文件 |

### 单项执行

也可以指定单项：

```
严格按照 docs/UPGRADE_DESIGN.md 设计文档，只实现 P1-3（售后 Agent 对接 MySQL 真实数据）这一项。
```

### 执行后验证

每批完成后，建议手动检查：

```bash
# 1. Python import 检查
cd backend/app && python -c "from api.main import create_fast_api; print('OK')"

# 2. 运行现有测试
cd backend/app && pytest tests -m "not integration" -v

# 3. 前端构建检查
cd front/agent_web_ui && npm run build
```

### 注意事项

- 如果执行模型的上下文窗口有限，建议按批次执行而非全量
- P1-4（上下文压缩）将 `prepare_history` 改为异步方法，会影响 `agent_service.py` 的调用方式，确保模型注意到这个连锁修改
- P2-4（限流）需要注意循环导入问题，设计文档已给出解决方案（独立 `rate_limiter.py` 模块）
- openai-agents SDK 的 Guardrail API（P1-1）取决于具体安装的版本，如果 import 路径不对，需要模型根据实际 SDK 版本调整
