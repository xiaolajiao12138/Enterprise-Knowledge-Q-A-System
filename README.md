# 企业内部知识问答平台（RAG 知识库问答系统）

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Frontend-Vue3-4FC08D.svg)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/UI-Element_Plus-409EFF.svg)](https://element-plus.org/)
[![LangChain](https://img.shields.io/badge/Framework-LangChain-1C3C3C.svg)](https://www.langchain.com/)
[![Chroma](https://img.shields.io/badge/VectorDB-Chroma-FF6F00.svg)](https://www.trychroma.com/)

企业级私有化 RAG（Retrieval-Augmented Generation，检索增强生成）知识问答平台。支持企业内部多格式文档（PDF、Word、TXT、Markdown）的上传、文本提取、切片（Chunking）、向量嵌入入库（Chroma）、智能向量检索、基于严格文档上下文的内容推理生成，并**在每个回答末尾明确标注引用来源**，彻底杜绝大模型幻觉编造。

---

## 一、系统架构与技术选型

- **架构设计**：前后端分离架构，基于 RESTful API 通信
- **后端框架**：Python 3.12 + FastAPI + Uvicorn
- **知识库与 RAG 链路**：LangChain + RecursiveCharacterTextSplitter + Chroma 向量数据库 (持久化到磁盘)
- **关系型数据库**：SQLite 3 + SQLAlchemy ORM（单文件免配置，方便私有化演示与快速启动，易于平滑迁移 MySQL）
- **安全鉴权**：JWT (JSON Web Token) + Bcrypt 强加密算法
- **前端技术栈**：Vue 3 + Vite + Element Plus + Pinia + Vue Router + Marked + Axios

---

## 二、系统目录结构

```text
企业知识问答系统/
├── 启动系统.bat                    # Windows 一键全自动启动脚本 (前后端+浏览器)
├── README.md                      # 完整项目部署与架构文档
├── docs/                          # 系统文档与技术沉淀
│   ├── RAG知识库问答系统全链路分步教程.md  # 工业级 RAG 深度工作原理与实战教程
│   └── superpowers/plans/
├── backend/                       # 后端工程 (FastAPI + LangChain + Chroma)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI 应用程序入口，CORS，中间件，异常捕获
│   │   ├── config.py              # 全局配置中心 (路径、JWT、默认模型参数)
│   │   ├── database.py            # SQLite / SQLAlchemy 引擎与 Session 依赖
│   │   ├── core/                  # 安全核心组件
│   │   │   ├── __init__.py
│   │   │   ├── security.py        # Bcrypt 密码哈希与 JWT 编解码
│   │   │   ├── deps.py            # FastAPI 依赖注入 (登录校验、管理员权限校验)
│   │   │   └── logger.py          # 系统运行日志与文档日志持久化工具
│   │   ├── models/                # 数据库 ORM 实体模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py            # 用户表 (User)
│   │   │   ├── document.py        # 知识库文档元数据表 (Document)
│   │   │   ├── chat.py            # 会话与问答历史消息表 (ChatSession, ChatMessage)
│   │   │   └── system_setting.py  # 动态配置表与系统日志表 (SystemSetting, SystemLog)
│   │   ├── schemas/               # Pydantic 请求与响应数据结构定义
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── chat.py
│   │   │   └── setting.py
│   │   ├── services/              # 业务服务核心层
│   │   │   ├── __init__.py
│   │   │   ├── document_parser.py # 多格式解析器 (PDF, DOCX, TXT, MD)
│   │   │   ├── text_splitter.py   # 中文智能递归切片分块
│   │   │   ├── vector_store.py    # Chroma 向量数据库管理 (增删查改、兜底容灾)
│   │   │   ├── rag_service.py     # RAG 核心推理引擎 (Prompt约束、防幻觉、引用提取)
│   │   │   └── background_tasks.py# 异步文档解析与切片向量化任务
│   │   └── api/                   # RESTful API 路由模块
│   │       ├── __init__.py
│   │       ├── auth.py            # 登录、退出、当前用户信息
│   │       ├── users.py           # 用户增删改查、重置密码 (管理员)
│   │       ├── documents.py       # 文档上传、列表、预览、删除、重新切片、向量库清空
│   │       ├── chat.py            # 会话管理、多轮问答提问、历史记录导出 CSV
│   │       └── settings.py        # 动态大模型参数、切片配置、连通性测试、日志查询
│   ├── data/                      # 运行时数据持久化目录
│   │   ├── uploads/               # 上传的源文档存储目录
│   │   ├── chroma_db/             # Chroma 向量库本地持久化目录
│   │   ├── demo_docs/             # 预置企业测试文档 (考勤管理办法、安全保密规范)
│   │   └── rag_system.db          # SQLite 数据库文件
│   ├── init_db.py                 # 初始化数据库表结构与默认账号
│   ├── import_demo_data.py        # 一键导入并向量化预置企业演示文档
│   ├── requirements.txt           # Python 依赖清单
│   └── run.py                     # 后端服务一键启动入口
└── frontend/                      # 前端工程 (Vue 3 + Element Plus)
    ├── index.html
    ├── package.json               # 前端依赖配置
    ├── vite.config.js             # Vite 构建与开发代理配置
    └── src/
        ├── App.vue                # 根组件 (配置 Element Plus 中文语言包)
        ├── main.js                # 前端主入口
        ├── assets/                # 样式与静态资源
        ├── api/                   # Axios API 请求封装与拦截器
        ├── store/                 # Pinia 状态管理 (用户凭据、角色)
        ├── router/                # Vue Router 路由配置与角色导航守卫
        ├── layout/                # 系统中后台响应式布局
        └── views/                 # 页面视图组件
            ├── login/index.vue    # 用户登录页 (支持快速体验预填)
            ├── chat/index.vue     # 核心问答对话页 (会话树、Markdown气泡、引用来源卡片)
            ├── knowledge/index.vue# 知识库管理页 (拖拽上传、切片进度、内容预览、清空向量库)
            ├── users/index.vue    # 用户管理页 (角色分配、启禁用、重置密码)
            └── settings/index.vue # 系统设置页 (模型切换、在线连通测试、日志审计)
```

---

## 三、核心功能与业务特性

### 1. 知识库模块 (管理员)
- **多格式支持**：支持 `.pdf`、`.docx`、`.txt`、`.md` 格式。
- **文件大小限制**：单文件最大支持 **20MB**。
- **异步解耦处理**：采用 FastAPI `BackgroundTasks`，文档上传后瞬间返回，后台异步解析、切片与向量化，不阻塞 HTTP 线程。
- **切片参数自适应**：支持后台动态配置 `chunk_size` 与 `chunk_overlap`，并支持对已有文档一键“重新向量化”。
- **文档管理与预览**：支持查看解析状态（处理中 / 成功 / 失败）、切片数量、文本内容 Drawer 抽屉预览、删除物理文件及向量。
- **向量库状态管理**：实时查看 Chroma 当前向量总数，支持一键清空向量库。

### 2. 问答对话模块 (全部登录用户)
- **多会话管理**：左侧展示历史会话列表，支持新建对话、会话重命名、删除会话、清空当前消息。
- **智能 RAG 推理**：
  1. 提取用户最新提问，执行 Chroma 向量语义检索获取 Top-K 片段；
  2. 针对上下文做相似度阈值清洗（过滤噪音）；
  3. 整合多轮历史对话上下文与严格防幻觉 Prompt，送入大模型生成；
  4. 每条答案底部展示折叠式【**引用来源**】卡片，包含引用的文档名称、切片序号、匹配度及内容预览。
- **严格防幻觉规则**：当知识库中检索不到匹配信息或相似度不足时，强制标准回复：`"知识库中暂未检索到与该问题相关的信息，无法为您解答。请尝试更换提问方式或联系管理员补充相关文档。"`，严禁 LLM 自行编造。
- **数据导出**：支持一键导出问答记录为 **CSV**，内置 `UTF-8 BOM`，彻底解决 Excel 打开乱码问题。

### 3. 多角色权限管理 (RBAC)
- **系统管理员 (admin)**：拥有全部权限（知识库上传/删除/重向量化/清空、用户管理、系统参数配置、日志审计）。
- **普通员工 (staff)**：仅能使用问答对话功能、查看并导出自己的问答历史，**无权上传、修改或删除知识库**；访问管理员 API 强制拦截返回 403 Forbidden。
- **用户管理**：管理员可新增账号、设置初始密码、随时启用/禁用员工账号、重置密码。

### 4. 系统动态配置与日志审计 (管理员)
- **大模型动态切换**：
  - **Ollama 本地模型**：如 `qwen2:7b`、`llama3:8b`、`chatglm3`，实现 100% 数据私有化、不离网。
  - **第三方 OpenAI 兼容 API**：如 DeepSeek、通义千问、Kimi、LocalAI、vLLM 等。
  - **参数自由调节**：动态调整 Base URL、API Key、Model Name、Temperature、Top-P、Top-K 检索数。
- **连通性测试**：在前端设置页可一键测试大模型端点连通性并实时展示请求耗时与检测到的本地模型。
- **日志审计**：记录用户认证、文档处理、问答交互和系统配置修改日志，支持按模块和级别筛选，提供错误堆栈查看。

---

## 四、快速上手与启动指南

### 方式一：Windows 一键启动（最简便）

双击项目根目录下的 **`启动系统.bat`**：
1. 脚本会自动初始化 SQLite 数据库及默认账号；
2. 自动在新窗口中启动后端 FastAPI 服务（`http://127.0.0.1:8000`）；
3. 自动启动前端 Vue3 开发服务（`http://127.0.0.1:3000`）；
4. 自动打开默认浏览器访问系统。

---

### 方式二：手动分步安装与启动

#### 1. 环境准备
- **Python**：>= 3.10（推荐 Python 3.12）
- **Node.js**：>= 18.0

#### 2. 后端安装与启动
```bash
# 1. 进入 backend 目录
cd backend

# 2. 安装 Python 依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 初始化数据库与默认管理员账号
python init_db.py

# 4. (可选) 导入预置企业演示文档并完成向量切片入库
python import_demo_data.py

# 5. 启动后端服务
python run.py
```
- 后端服务地址：`http://127.0.0.1:8000`
- 交互式 Swagger API 文档：`http://127.0.0.1:8000/docs`

#### 3. 前端安装与启动
```bash
# 打开新终端，进入 frontend 目录
cd frontend

# 安装依赖
npm install --registry=https://registry.npmmirror.com

# 启动前端开发服务器
npm run dev
```
- 前端页面地址：`http://localhost:3000`

---

## 五、默认体验账号

系统初始化时已内置两个不同权限的账号，登录页面下方提供了**一键预填按钮**：

| 用户名 | 登录密码 | 系统角色 | 具备权限 |
| :--- | :--- | :--- | :--- |
| **admin** | **admin123** | **系统管理员** | 完整最高权限（上传文档、删除知识库、清空向量库、用户管理、系统参数配置、日志审计） |
| **staff** | **staff123** | **普通员工** | 仅问答交互、历史记录查看与导出；无权进入管理页面 |

---

## 六、本地私有化大模型接入配置 (Ollama)

若需要在完全离线或无外网环境下运行，可搭配 [Ollama](https://ollama.com/)：

1. 本地安装 Ollama 并下载中文大模型与 Embedding 模型：
   ```bash
   ollama run qwen2:7b
   ollama pull nomic-embed-text
   ```
2. 使用管理员登录本系统，进入【**系统配置**】页面：
   - 模型服务商：选择 `本地私有化部署 (Ollama)`
   - API 基地址：`http://127.0.0.1:11434`
   - 推理模型：`qwen2:7b`
   - Embedding 模型：`nomic-embed-text`
   - 点击【**测试大模型接口连通性**】确认通信成功，点击【**保存系统配置**】即可。

> **提示**：即便本地尚未启动 Ollama，系统也内置了智能本地高鲁棒提取与向量兜底机制，不会发生崩溃，开箱即可体验上传、检索与问答全流程。

---

## 七、常见问题与注意事项

1. **单文件上传超过 20MB**：
   后端与前端均配置了 20MB 大小硬拦截，超限时会给出明确的中文友好提示。
2. **导出 CSV 中文在 Excel 打开乱码**：
   导出的 CSV 文件头部写入了标准 `UTF-8 BOM (\ufeff)` 签名，在 Windows Excel、WPS 或 Mac Numbers 中均可直接双击正常打开。
3. **幻觉与不编造测试**：
   系统具备严格的知识库边界校验。若询问知识库中不存在的事件，系统会如实回复“知识库中暂未检索到与该问题相关的信息”，杜绝臆测。

---

## 八、系统底层工作原理与全链路技术教程

针对研发人员、架构师与系统维护人员，项目提供了深入浅出的分步原理教程：
👉 **[点击查阅：RAG 知识库问答系统全链路分步教程 (docs/RAG知识库问答系统全链路分步教程.md)](./docs/RAG知识库问答系统全链路分步教程.md)**

涵盖：
- **第一大部分：文档入库流程**（项目配置、所有 Python 依赖包角色、仿射空间 PDF 提取、切片分块调参、Embedding 向量化、Chroma 持久化）；
- **第二大部分：用户在线问答检索流程**（Query 向量化、余弦相似度、中文跳字混合召回、防幻觉 Prompt 注入、LLM 生成与溯源卡片）；
- **生产调优与排坑手册**（各环节 I/O 矩阵对照、时区问题、断裂错位、幻觉抑制技巧）。
   系统在 Prompt 层与检索评分层实施了双重硬约束。尝试提问知识库中不存在的问题（例如“公司的股票代码是多少”），系统会准确拒绝并回复无相关资料，绝不自行编造。
