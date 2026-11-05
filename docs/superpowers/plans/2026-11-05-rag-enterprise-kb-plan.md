# 企业内部知识问答平台（RAG 知识库问答系统）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个完整的企业内部 RAG 知识库问答系统，包含 FastAPI 后端、Vue3+ElementPlus 前端、Chroma 向量库、SQLite 关系数据库、JWT 鉴权、多角色权限控制、文档解析切片向量化、引用来源标注以及私有化大模型接入配置。

**Architecture:** 前后端分离架构。后端采用 FastAPI 提供 RESTful API 与后台异步任务处理；向量数据库使用 Chroma，关系数据库使用 SQLite (SQLAlchemy)；LangChain 负责文本切片与向量检索链路；前端使用 Vite + Vue3 + Element Plus + Pinia + Vue Router 构建现代化中后台管理与问答交互界面。

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, LangChain, ChromaDB, SQLAlchemy, SQLite, Pydantic, Vue 3, Vite, Element Plus, Pinia, Axios.

**Spec:** 用户提供的《企业内部知识问答平台（RAG 知识库问答系统）》需求规格说明书。

## Global Constraints
- 回答必须明确标注引用来源（文档名、切片/位置、相似度预览）
- 检索上下文不足以回答问题时，严格禁止编造，输出标准固定回复
- 多轮对话携带历史上下文，但检索知识库以最新用户问题为主
- 单文件上传最大限制为 20MB，支持格式为 PDF、DOCX、TXT、MD
- 管理员与普通员工角色严格鉴权分离
- 全局中文注释与提示

## Review Focus
1. 大文件（接近 20MB）或者格式异常的损坏文件上传时，后台异步任务需要安全捕获异常并标记文档状态为“失败”，不可导致整个应用崩溃。
2. LLM 服务超时或配置错误（如 Ollama 未启动或 API Key 无效）时，需优雅捕获异常并向前端返回友好中文错误，而非 500 堆栈崩溃。
3. 知识库中没有任何匹配文档或相似度过低时，Prompt 严格约束 LLM 返回“知识库中暂未检索到相关内容”。
4. 普通员工访问知识库管理、用户管理、系统配置接口时，后端强制通过 Depend 校验角色，返回 403 Forbidden。
5. 导出问答历史 CSV 时，需正确处理 UTF-8 带 BOM，防止 Excel 打开中文乱码。

---

### Task 1: 项目骨架与后端核心架构搭建
- 创建完整的目录结构：`backend/`, `frontend/`, `docs/`
- 编写 `backend/requirements.txt`
- 编写 `backend/app/config.py`，管理系统配置（JWT 密钥、上传路径、向量库持久化路径、默认 LLM 与 Embedding 配置）
- 编写 `backend/app/database.py`，配置 SQLite 引擎与 SQLAlchemy Base Session
- 编写 `backend/app/core/logger.py`，配置系统运行日志与文档日志处理模块

### Task 2: 数据模型与用户鉴权模块 (RBAC)
- 编写 `backend/app/models/`：
  - `user.py`：用户表（id, username, hashed_password, role, is_active, created_at）
  - `document.py`：文档表（id, filename, file_path, file_size, file_type, status, error_msg, chunk_count, created_at）
  - `chat.py`：会话与消息表（ChatSession, ChatMessage，包含 query, answer, sources_json 等）
  - `system_setting.py`：系统配置键值表与系统日志表
- 编写 `backend/app/schemas/` 对应的 Pydantic 数据模式
- 编写 `backend/app/core/security.py`（密码哈希与 JWT 令牌生成/校验）与 `backend/app/core/deps.py`（用户注入与管理员鉴权）
- 编写 `backend/app/api/auth.py` 与 `backend/app/api/users.py`（登录、登出、获取用户信息、用户增删改查、重置密码）
- 编写 `backend/init_db.py`：初始化数据库结构并自动创建默认管理员 `admin` / `admin123`

### Task 3: 知识库文档解析、切片与 Chroma 向量库服务
- 编写 `backend/app/services/document_parser.py`：支持 PDF、DOCX、TXT、MD 文本提取
- 编写 `backend/app/services/text_splitter.py`：根据系统配置的 chunk_size 和 chunk_overlap 递归切块
- 编写 `backend/app/services/vector_store.py`：管理 ChromaDB 客户端与向量检索集合，支持动态切换 Embedding 模型、添加切片、按 document_id 删除向量、清空集合、统计向量总数
- 编写 `backend/app/services/background_tasks.py`：异步处理文档解析与向量化存储，实时更新文档状态与切片数
- 编写 `backend/app/api/documents.py`：文档上传（20MB大小校验、格式校验）、文档列表、文档删除、重新向量化、文档预览、向量库概览统计与清空接口

### Task 4: RAG 问答核心服务与对话管理
- 编写 `backend/app/services/rag_service.py`：
  - 接入 Ollama 本地模型与 OpenAI 兼容 API
  - 动态检索 TopN 相关片段并计算相似度
  - 严格 Prompt 注入：基于提供的文档片段作答，无信息明确拒绝，多轮历史上下文注入
  - 结构化提取引用来源（文档名称、片段序号、预览内容）
- 编写 `backend/app/api/chat.py`：
  - 创建新会话、获取会话列表、删除会话、清空会话
  - 发送提问接口（支持流式/非流式响应、关联引用来源）
  - 获取会话历史消息记录
  - 导出用户对话记录为 CSV（UTF-8-SIG 编码防止 Excel 乱码）

### Task 5: 系统设置、日志管理与后端主入口装配
- 编写 `backend/app/api/settings.py`：获取与更新 LLM 配置、切片参数、向量模型配置、测试模型连通性、分页查询系统运行日志与文档处理日志
- 编写 `backend/app/main.py`：整合所有路由、CORS 中间件、全局异常处理、静态文件上传路径挂载、Swagger 文档路径配置
- 编写 `backend/run.py`：支持 `python run.py` 一键启动后端
- 创建测试演示文档 `backend/data/demo_docs/`（如《企业员工入职与考勤制度》、《信息技术与数据安全规范》）

### Task 6: Vue3 前端工程初始化与通用架构
- 创建 `frontend/package.json`、`vite.config.js`、`index.html`
- 安装与配置 Vue 3、Vite、Element Plus (中文包)、Vue Router、Pinia、Axios、Lucide / Element Plus 图标库
- 封装 Axios 请求拦截器与响应拦截器（Token 自动附带、401 自动跳转登录、403 权限提示、网络错误友好提示）
- 编写状态管理库 `src/store/user.js` 与 `src/store/chat.js`
- 编写路由配置 `src/router/index.js`，包含路由导航守卫与管理员角色权限拦截
- 编写系统主布局组件 `src/layout/index.vue`（顶部导航、侧边栏折叠、用户头像下拉菜单、角色徽章）

### Task 7: 前端核心业务页面实现
- 编写登录页面 `src/views/login/index.vue`：现代简洁设计，表单校验，登录成功后跳转
- 编写问答对话页面 `src/views/chat/index.vue`：
  - 左侧历史会话列表（新建对话、切换会话、重命名/删除会话、清空记录、导出 CSV 按钮）
  - 右侧对话视窗（多轮对话气泡、用户头像、AI 头像、Markdown 代码高亮渲染）
  - 答案底部展开式【引用来源】卡片（文档名称、片段序号、匹配内容预览）
  - 快捷提问推荐提示、发送快捷键支持（Enter 发送，Shift+Enter 换行）
- 编写知识库管理页面 `src/views/knowledge/index.vue`：
  - 顶部向量库概览统计（文档总数、向量总数、清空向量库按钮）
  - 拖拽文档上传组件（限制 20MB，支持 .pdf, .docx, .txt, .md）
  - 文档列表表格（文件名、大小、切片数、状态 Badge：处理中/成功/失败、上传时间、操作列）
  - 操作功能：文档预览 Drawer、重新向量化按钮、删除文档确认
- 编写用户管理页面 `src/views/users/index.vue`：用户列表、新增用户 Dialog、启禁用 Switch、重置密码 Dialog
- 编写系统设置页面 `src/views/settings/index.vue`：
  - 模型配置 Tab（Ollama / 第三方 OpenAI 兼容 API、Base URL、API Key、模型名、温度、Top-P、Top-N 检索数、连通性测试按钮）
  - 切片配置 Tab（Chunk Size、Chunk Overlap）
  - 系统日志与文档处理日志查看 Tab（支持分页刷新与按级别筛选）

### Task 8: 系统联调、一键启动脚本与使用部署文档
- 编写 Windows 一键启动脚本 `启动系统.bat`（自动检查 Python/Node、初始化数据库、后台同时启动前后端服务并打开浏览器）
- 编写完善详细的 `README.md`，包含环境准备、手动安装启动步骤、管理员初始化、系统界面介绍、Ollama 本地配置指南、接口文档访问方式
- 全流程测试：管理员登录、文档上传解析向量化、知识库问答检索、引用来源展示、历史记录导出、系统配置修改、普通员工权限隔离验证
