# AI 应用开发与 Agent 工程：第 1--20 课总结

面向岗位：AI 应用开发工程师、AI Agent 工程师、高级 AI 应用研发工程师\
技术栈：Python、FastAPI、Pydantic、AsyncIO、Groq API、SSE、Tool
Calling、Agent Loop、PostgreSQL。

> 使用说明：这份文档用于面试复习与 GitHub
> 归档。项目讲解应以自己真实实现、运行和验证过的代码为准；教学原型不要描述成已上线的生产系统。

## 1. 前 20 课的主线

前 20 课的目标，是从"调用一次大模型
API"逐步构建出有工程边界、能处理错误、支持工具调用和会话记忆的 AI 后端。

``` text
用户请求
  ↓
FastAPI API 层 → Pydantic 输入校验
  ↓
Service / Agent 业务层
  ↓
LLM Client（Groq）
  ├─ 普通对话 / Streaming
  └─ Tool Calling → 服务端校验 → 工具执行 → 工具结果回传
  ↓
Memory（会话历史）→ PostgreSQL 持久化
  ↓
Context Manager（决定本轮发送给模型的上下文）
```

## 2. 第 1--20 课知识地图

  ----------------------------------------------------------------------------------------------------------------
  课程                    主题                    关键知识
  ----------------------- ----------------------- ----------------------------------------------------------------
  1                       AI 应用与工程分层       模型不是完整应用；API、Service、LLM Client 的职责

  2                       Python 类型与数据模型   函数、类、模块、类型注解、数据结构

  3                       Pydantic                `BaseModel`、`Field`、运行时输入校验

  4                       异常与日志              自定义异常、异常边界、`logging`、避免吞错

  5                       AsyncIO                 `async`、`await`、IO 密集型并发、避免阻塞事件循环

  6                       FastAPI                 路由、请求/响应模型、依赖与业务分层

  7                       Streaming 基础          `yield`、生成器、`AsyncGenerator`、流式响应

  8                       SSE                     `text/event-stream`、事件分隔、`StreamingResponse`、前端流读取

  9                       LLM Client 抽象         Mock 与真实模型实现、供应商隔离、配置管理

  10                      Groq API                环境变量、异步聊天请求、模型配置、资源关闭

  11                      Prompt 与多轮上下文     System/User/Assistant 消息；历史需显式传给模型

  12                      结构化输出              JSON 解析、Pydantic 校验、输出失败处理

  13                      Function Calling        模型生成工具调用请求，服务端负责执行

  14                      Tool Registry           工具白名单、参数解析与验证、权限边界

  15                      Agent Loop              模型决策 → 工具执行 → 结果回传 → 模型继续或结束

  16                      Agent State             决策轮次、工具调用次数、状态与停止条件

  17                      故障恢复                超时、有限重试、指数退避、错误分类、工具失败反馈

  18                      会话记忆                按 `conversation_id` 加载/保存历史；内存存储的局限

  19                      PostgreSQL 持久化       `asyncpg`、连接池、事务、会话表与消息表

  20                      Context Window          完整历史与本轮上下文分离；控制 Token 和消息完整性
  ----------------------------------------------------------------------------------------------------------------

## 3. 核心知识点

### 3.1 分层架构

-   **API 层**：HTTP、请求校验、响应格式和状态码。
-   **Service / Agent 层**：业务流程与模型/工具编排，不依赖 HTTP 细节。
-   **LLM Client 层**：封装模型供应商
    SDK、请求参数、超时、重试和响应处理。
-   **Memory / Repository 层**：管理会话、消息和持久化。

分层让模型供应商可替换、业务逻辑可独立测试，也能避免路由函数变成难以维护的大函数。目录不必机械照搬，关键是职责边界清晰。

### 3.2 类型注解、dataclass 与 Pydantic

``` python
from dataclasses import dataclass
from pydantic import BaseModel, Field

@dataclass
class InternalMessage:
    content: str

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
```

-   类型注解主要服务于静态分析、IDE
    提示和可读性，不会自动校验所有运行时输入。
-   `dataclass` 用于减少数据类样板代码，不等于完整的输入校验。
-   Pydantic 在运行时解析和校验数据，适合 API 请求、配置和结构化输出。
-   Pydantic 的转换与严格校验行为取决于版本和配置。

**面试回答：** 我会在系统边界使用 Pydantic
验证外部输入；内部数据结构根据需求使用 dataclass
或普通类型定义，避免把类型标注误认为运行时校验。

### 3.3 AsyncIO 的作用与限制

模型 API、数据库、外部工具大多是 IO 密集型操作。`async/await`
能让协程在等待 IO 时让出执行权，提高单进程并发处理能力。

异步并不代表所有代码都会更快： - 同步阻塞调用仍会阻塞事件循环。 - CPU
密集型工作可能需要进程池或其他执行方式。 -
连接池、超时、并发上限依然重要。 - `asyncio.gather`
也需要考虑并发限制与失败传播。

### 3.4 Timeout、Retry、Backoff、Jitter、Fallback

-   **Timeout**：避免无限等待。
-   **Retry**：对可能暂时恢复的故障再次尝试。
-   **Exponential Backoff**：逐渐拉长重试间隔，减少持续冲击故障服务。
-   **Jitter**：加入随机抖动，避免大量请求同步重试。
-   **Fallback**：主方案失败后切换到替代方案，或返回受控降级结果。

应区分连接错误、超时、限流、服务端错误、参数错误和权限错误。只对适合重试的错误有限重试，并尊重供应商的重试提示。SDK
和业务层同时重试可能造成次数相乘。会产生副作用的工具还需要幂等设计。

### 3.5 Streaming、yield 与 SSE

-   `yield` 可逐段产出内容。
-   `AsyncGenerator` 可异步逐段产出内容。
-   FastAPI `StreamingResponse` 可将数据流式写入 HTTP 响应。
-   SSE 是基于 HTTP 的服务端推送格式，常见事件如下：

``` text
data: {"type":"token","content":"你好"}
```

SSE 事件通常以空行结束。**网络 chunk 不等于完整 SSE
事件**：一个事件可能被拆成多个 chunk，一个 chunk
也可能包含多个事件。客户端需要缓冲并按协议解析，不能假设每个 chunk
都是一条完整消息。

生产实现还应考虑断连清理、错误事件、结束标记、代理缓冲、心跳和超时。

### 3.6 多轮对话与 Prompt

大多数无状态聊天 API
不会自动记住上一次独立请求。每次调用都要传入本轮需要的消息：

``` python
messages = [
    {"role": "system", "content": "你是一个有帮助的助手。"},
    {"role": "user", "content": "我叫小林。"},
    {"role": "assistant", "content": "你好，小林。"},
    {"role": "user", "content": "我叫什么？"},
]
```

应用负责管理历史、选择上下文，并在必要时做摘要或检索。完整历史存储和本轮发送给模型的上下文不是同一个概念。

### 3.7 结构化输出为什么仍需校验？

要求模型返回 JSON，不保证它一定返回合法
JSON，也不保证字段满足业务规则。可靠流程通常包括：明确输出结构、解析、Pydantic
校验、有限恢复或返回错误，以及服务端业务规则校验。关键业务操作不能只相信模型输出。

### 3.8 Function Calling / Tool Calling

模型根据用户问题和工具 Schema
生成结构化调用请求；后端解析、校验参数、检查权限、执行真实函数，再把结果作为对应
tool 消息回传模型。

``` text
用户问题
  ↓
模型输出工具名 + arguments
  ↓
服务端白名单、参数、权限检查
  ↓
执行真实工具函数
  ↓
工具结果关联 tool_call_id 并回传模型
  ↓
模型继续决策或输出最终回答
```

**核心边界：模型提出调用意图，后端决定是否允许并执行。**
模型不会因为生成了 `function.name` 就自动运行本地 Python 函数。

生产中还应考虑工具权限、参数范围、超时、审计日志、输出大小、敏感信息，以及高风险操作的用户确认。

### 3.9 Agent Loop 与 Agent State

普通 LLM 调用通常是一次请求、一次回答；Agent
会围绕目标进行多轮决策，根据需要调用工具，再根据工具结果继续，直到完成或达到停止条件。

``` python
for _ in range(max_steps):
    response = await request_model(messages)
    assistant_message = response.choices[0].message

    if not assistant_message.tool_calls:
        return assistant_message.content or ""

    messages.append(
        assistant_message.model_dump(exclude_none=True)
    )

    for tool_call in assistant_message.tool_calls:
        # 真实实现必须做白名单、参数和权限检查。
        result = await execute_tool_safely(tool_call)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        })

raise RuntimeError("Agent 达到最大决策轮次")
```

这是核心流程示例，`execute_tool_safely` 需要由应用实现。

必须区分： - **决策轮次**：模型被请求做一次决策/生成。 -
**工具调用次数**：实际执行了多少次工具。 -
**最终回答**：模型不再要求调用工具，返回面向用户的内容。

一次模型决策可以请求多个工具，因此两种计数不一定相等。

Agent 应设置
`max_steps`、`max_tool_calls`、模型与工具超时、有限重试、日志和成本指标，避免循环、重复调用和费用失控。

### 3.10 Memory 与 Context Manager

-   **Memory** 负责历史保存在哪里、如何取回。
-   **Context Manager** 负责本轮究竟发送哪些内容给模型。

课程中的记忆演进： 1. 进程内字典：实现简单，但进程重启后丢失。 2.
PostgreSQL：持久化保存会话与消息。 3. Context
Manager：从完整历史中选择本轮上下文，控制 Token 和成本。

上下文裁剪不能随意截断消息。assistant 的 tool call 与对应 tool result
必须保持关联；实际系统应按 Token 预算选择完整对话轮次，结合摘要与检索。

### 3.11 PostgreSQL 会话存储

课程采用会话表与消息表的基础设计：

``` sql
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    conversation_id TEXT NOT NULL
        REFERENCES conversations(id) ON DELETE CASCADE,
    sequence_no BIGINT NOT NULL,
    role TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (conversation_id, sequence_no)
);
```

-   `JSONB` 可保存不同类型的消息载荷。
-   `sequence_no` 用于确定消息顺序。
-   外键保证消息关联有效会话；`ON DELETE CASCADE`
    可在删除会话时清理关联消息。
-   `asyncpg` 连接池可复用数据库连接；事务用于保证一组写操作的原子性。

教学版若每次保存都删除并重写完整历史，可能在并发请求时产生覆盖问题。生产环境应考虑增量写入、稳定消息
ID、幂等、并发控制和用户会话授权。

------------------------------------------------------------------------

## 4. 面试高频问题速答

### Q1：你如何设计可维护的 AI 后端？

我会将 HTTP 接口、业务编排和模型供应商调用分层。API 层用 FastAPI 和
Pydantic 处理请求边界；Service/Agent 层编排业务；LLM Client 封装供应商
SDK、超时、重试和错误映射；数据访问通过独立模块管理。这样便于替换模型、独立测试和定位故障。

### Q2：模型 API 超时怎么处理？

先设置明确超时，再区分连接失败、限流、服务端错误、参数错误和权限错误。对可恢复错误采用有限重试和退避，并尊重服务端重试提示；对不可重试错误直接失败。避免
SDK 与业务层重复重试，并记录耗时、尝试次数和错误类型。

### Q3：如何实现安全的 Tool Calling？

模型只生成调用请求，服务端不直接相信它。后端从白名单查找工具实现，解析和校验参数、检查用户权限、设置超时并执行。高风险或有副作用的操作需要授权/确认、审计和幂等处理。错误向
Agent 返回受控信息，不暴露堆栈或密钥。

### Q4：为什么 Agent 会多次请求模型？

每轮都要根据当前消息和工具结果决定下一步。模型可能先调用工具，收到结果后继续调用其他工具，最后再生成答案。因此一次用户请求可能对应多轮模型请求。应通过最大步骤、工具次数和超时限制成本与循环风险。

### Q5：上下文过长怎么处理？

区分完整历史存储和本轮上下文。完整历史可存数据库；发送前按 Token
预算选择系统提示、当前问题、最近完整轮次、必要工具结果和摘要。不能仅按字符数粗暴截断，也不能破坏
tool call 与 tool result 的对应关系。

### Q6：怎么测试 Agent？

-   单元测试：参数解析、工具白名单、状态转换、上下文裁剪和错误分类。
-   Mock 测试：模拟模型响应与工具结果，减少对真实 API 的依赖。
-   集成测试：测试 Groq、PostgreSQL 与工具调用链路。
-   回归评估：固定问题集，检查工具选择、答案质量、引用、延迟和成本。
-   安全测试：越权访问、恶意文档指令、无效参数、重复副作用和敏感信息泄露。

### Q7：如何降低 AI 应用成本？

控制上下文长度和最大 Agent
步数；避免无意义工具调用；按任务选择模型；缓存可复用结果；限制重试；记录
Token、延迟和失败率；用评估集验证降本后质量是否下降。成本不仅取决于单次价格，也取决于完成任务所需调用次数和成功率。

### Q8：模型生成的 JSON 或工具参数可信吗？

不可信。模型输出属于外部输入，需要解析、Schema
校验、业务规则校验和权限检查。关键决策由服务端控制，不能仅凭模型返回的字段就执行付款、删除或发送消息等操作。

------------------------------------------------------------------------

## 5. 项目介绍模板

> 我实现了一个基于 Python、FastAPI 和 Groq API 的 AI Agent
> 练习项目，从基础聊天逐步扩展到流式输出、工具调用、Agent
> Loop、会话记忆和上下文管理。
>
> 工程上，我将 API、业务编排、LLM
> Client、记忆存储和上下文管理拆分开。使用 Pydantic
> 校验外部输入，使用异步调用处理模型和数据库
> IO；通过超时、有限重试、指数退避和步骤上限控制故障与成本。
>
> Agent 通过工具 Schema
> 获取可用工具信息。模型返回调用请求后，服务端进行白名单和参数检查，再执行工具并把结果关联到对应的
> tool call。会话历史可以保存到 PostgreSQL，每次发给模型的消息由 Context
> Manager 按上下文预算筛选。
>
> 下一步会补充自动化测试、可观测性、RAG
> 评估、权限隔离和并发安全，并通过固定测试集评估工具选择、回答质量、延迟与成本。

**诚信提醒：**
只描述你真实写过、运行过并能解释的功能。仍属于教学原型的部分，应明确说是原型或学习项目，而不是已经上线的生产系统。

------------------------------------------------------------------------

## 6. 推荐的 GitHub 文档结构

``` text
ai-agent-training/
├── README.md
├── docs/
│   ├── lessons-01-20-summary.md
│   ├── interview-qa.md
│   └── architecture.md
├── app/
├── tests/
├── .env.example
├── .gitignore
└── requirements.txt
```

建议： - `README.md`：项目目标、技术栈、功能、安装和运行。 -
`docs/lessons-01-20-summary.md`：本总结。 -
`docs/interview-qa.md`：高频面试问答。 -
`docs/architecture.md`：架构图、数据流、错误处理和设计取舍。

### Git 提交命令

``` bash
git add docs/lessons-01-20-summary.md
git commit -m "docs: summarize AI agent lessons 1-20 for interview prep"
git push
```

如果文档放在仓库根目录，请相应修改 `git add`
的路径。推送前确认远端地址和当前分支。

------------------------------------------------------------------------

## 7. 面试自测清单

-   [ ] 能画出 API → Service/Agent → LLM Client → Tool/Memory 的架构。
-   [ ] 能解释 Pydantic 与类型注解的区别。
-   [ ] 能解释 async/await 为什么适合 IO 密集型 API。
-   [ ] 能说清 Timeout、Retry、Backoff 和 Jitter 的区别。
-   [ ] 能解释网络 chunk 为什么不等于完整 SSE 事件。
-   [ ] 能解释 Function Calling 中模型与后端的职责边界。
-   [ ] 能手绘 Agent Loop，并区分决策轮次和工具调用次数。
-   [ ] 能解释 `tool_call_id` 为什么要与工具结果对应。
-   [ ] 能解释进程内记忆、PostgreSQL 持久化与 Context Manager 的区别。
-   [ ] 能指出教学实现的局限和生产环境需要的保护措施。
-   [ ] 能演示一个真实运行过的请求，并解释日志、异常和测试策略。

## 8. 下一阶段学习路线

完成前 20 课后，进入 RAG： 1. 文档加载、清洗与 Chunking。 2. Embedding
与语义检索。 3. PostgreSQL + pgvector。 4. 混合检索、重排序和来源引用。
5. RAG 评估与权限过滤。 6. 将 RAG 封装为 Agent 可调用工具。

复习时，不要只背定义。对每个主题都练习：用自己的话解释原理、指出代码位置、描述失败场景，并说明设计取舍。
