<template>
  <div class="chat-container">
    <!-- 左侧会话历史面板 -->
    <div class="session-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" class="new-chat-btn" @click="handleCreateSession">
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
      </div>

      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: currentSessionId === session.id }"
          @click="selectSession(session.id)"
        >
          <el-icon class="session-icon"><ChatLineRound /></el-icon>
          <span class="session-title" :title="session.title">{{ session.title }}</span>

          <div class="session-actions" @click.stop>
            <el-button link size="small" @click="openRenameDialog(session)">
              <el-icon><EditPen /></el-icon>
            </el-button>
            <el-button link size="small" type="danger" @click="handleDeleteSession(session.id)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>

        <el-empty
          v-if="sessions.length === 0"
          description="暂无历史对话"
          :image-size="60"
        />
      </div>

      <div class="sidebar-footer">
        <el-button link size="small" @click="handleExportCsv">
          <el-icon><Download /></el-icon>
          导出问答记录 (CSV)
        </el-button>
        <el-button
          v-if="currentSessionId"
          link
          size="small"
          type="danger"
          @click="handleClearMessages"
        >
          <el-icon><DeleteFilled /></el-icon>
          清空当前对话
        </el-button>
      </div>
    </div>

    <!-- 右侧问答视窗 -->
    <div class="chat-main">
      <!-- 消息气泡流 -->
      <div ref="messageBoxRef" class="message-stream">
        <!-- 会话为空时的欢迎与快捷提问推荐 -->
        <div v-if="messages.length === 0" class="welcome-card">
          <div class="welcome-icon">
            <el-icon :size="40" color="#3b82f6"><ChatDotRound /></el-icon>
          </div>
          <h3>欢迎使用企业内部知识问答助手</h3>
          <p class="welcome-desc">
            系统已搭载企业内部文档库，针对您的提问实时检索最匹配的知识片段并生成答案，附带可溯源引用文档。
          </p>

          <div class="quick-questions">
            <div class="quick-title">您可以快速尝试提问：</div>
            <div class="question-chips">
              <el-tag
                v-for="(q, idx) in demoQuestions"
                :key="idx"
                class="chip-item"
                effect="plain"
                round
                @click="fillQuickQuestion(q)"
              >
                {{ q }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message-row"
          :class="msg.role"
        >
          <div class="avatar-box">
            <el-avatar v-if="msg.role === 'user'" class="user-avatar">我</el-avatar>
            <el-avatar v-else class="ai-avatar">AI</el-avatar>
          </div>

          <div class="message-bubble-wrapper">
            <div class="message-header-info">
              <span class="sender-name">{{ msg.role === 'user' ? '我的提问' : '知识库助手' }}</span>
              <span class="send-time">{{ formatTime(msg.created_at) }}</span>
            </div>

            <div class="bubble-content">
              <!-- 用户消息展示纯文本 -->
              <div v-if="msg.role === 'user'" class="text-content">
                {{ msg.content }}
              </div>
              <!-- AI 消息支持 Markdown 渲染 -->
              <div
                v-else
                class="markdown-body"
                v-html="renderMarkdown(msg.content)"
              />
            </div>

            <!-- 引用来源展示卡片 -->
            <div v-if="msg.sources && msg.sources.length > 0" class="sources-card">
              <div class="sources-toggle" @click="toggleSources(msg.id)">
                <el-icon><Document /></el-icon>
                <span>引用知识库来源 ({{ msg.sources.length }} 个片段)</span>
                <el-icon class="arrow-icon">
                  <ArrowDown v-if="!openedSources[msg.id]" />
                  <ArrowUp v-else />
                </el-icon>
              </div>

              <div v-show="openedSources[msg.id]" class="sources-list">
                <div
                  v-for="(src, sIdx) in msg.sources"
                  :key="sIdx"
                  class="source-item clickable"
                  @click="handleOpenSourceDetail(src)"
                >
                  <div class="source-top">
                    <span class="source-doc-name">
                      <el-icon><Files /></el-icon>
                      《{{ src.filename }}》
                    </span>
                    <el-tag size="small" type="info">切片序号: #{{ src.chunk_index }}</el-tag>
                    <el-tag v-if="src.score" size="small" type="success">匹配度: {{ (src.score * 100).toFixed(0) }}%</el-tag>
                    <div class="source-action-pill">
                      <el-icon><View /></el-icon>
                      <span>点击查看详情</span>
                    </div>
                  </div>
                  <div class="source-preview">{{ src.content_preview }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 思考中加载态 -->
        <div v-if="sending" class="message-row assistant">
          <div class="avatar-box">
            <el-avatar class="ai-avatar">AI</el-avatar>
          </div>
          <div class="message-bubble-wrapper">
            <div class="bubble-content thinking-bubble">
              <span class="dot-pulse">正在检索知识库并生成精准回答...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部输入区域 -->
      <div class="input-panel">
        <div class="input-wrapper">
          <el-input
            v-model="inputQuestion"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 5 }"
            placeholder="请输入您的问题... (按 Enter 发送，Shift + Enter 换行)"
            @keydown.enter.prevent="handleEnterSend"
          />
          <div class="input-actions">
            <span class="hint-text">严格基于知识库资料回答 · 杜绝幻觉编造</span>
            <el-button
              type="primary"
              :loading="sending"
              :disabled="!inputQuestion.trim()"
              @click="handleSend"
            >
              <el-icon><Promotion /></el-icon>
              发送提问
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 重命名会话 Dialog -->
    <el-dialog v-model="renameDialogVisible" title="修改会话标题" width="380px">
      <el-input v-model="editTitle" placeholder="请输入新会话名称" maxlength="30" show-word-limit />
      <template #footer>
        <el-button @click="renameDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRename">保存</el-button>
      </template>
    </el-dialog>

    <!-- 知识库引用来源详情与原文预览抽屉 -->
    <el-drawer
      v-model="sourceDrawerVisible"
      :title="`知识库引用详情 - 《${selectedSource.filename || '未知文档'}》`"
      size="620px"
      direction="rtl"
      destroy-on-close
    >
      <div v-if="selectedSource" class="drawer-source-container">
        <!-- 基础元数据栏 -->
        <div class="source-meta-bar">
          <div class="meta-tag-item">
            <span class="meta-label">命中切片：</span>
            <el-tag size="small" type="primary">#{{ selectedSource.chunk_index }}</el-tag>
          </div>
          <div class="meta-tag-item">
            <span class="meta-label">算法匹配度：</span>
            <el-tag size="small" type="success">{{ (selectedSource.score * 100).toFixed(0) }}%</el-tag>
          </div>
          <div class="meta-tag-item" v-if="selectedSource.page">
            <span class="meta-label">文档定位：</span>
            <el-tag size="small" type="info">第 {{ selectedSource.page }} 页/段</el-tag>
          </div>
        </div>

        <!-- 标签切换：命中切片 / 原文档解析全文 -->
        <el-tabs v-model="activeSourceTab" class="source-tabs" @tab-change="handleTabChange">
          <el-tab-pane label="当前命中切片内容" name="chunk">
            <div class="chunk-content-box">
              <div class="box-toolbar">
                <span class="toolbar-tip">大模型本次回答直接引用的知识库切片内容：</span>
                <el-button size="small" link type="primary" @click="copyChunkContent">
                  <el-icon><CopyDocument /></el-icon> 复制切片内容
                </el-button>
              </div>
              <div class="chunk-text-view">
                {{ selectedSource.content || selectedSource.content_preview }}
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="原文档全文预览" name="fullDoc">
            <div v-loading="docFullLoading" class="full-doc-box">
              <div class="box-toolbar">
                <span class="toolbar-tip" v-if="docFullData.total_pages">
                  共 {{ docFullData.total_pages }} 页/段，计 {{ docFullData.total_chars }} 字符
                </span>
                <span class="toolbar-tip" v-else>原文档提取内容：</span>
                <el-button
                  v-if="selectedSource.document_id"
                  size="small"
                  link
                  type="success"
                  @click="handleDownloadOriginDoc"
                >
                  <el-icon><Download /></el-icon> 下载原始文档
                </el-button>
              </div>
              <div class="full-doc-text-view">
                <pre v-if="docFullData.preview_text">{{ docFullData.preview_text }}</pre>
                <el-empty v-else-if="!docFullLoading" description="暂无法加载该文档上下文" :image-size="60" />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <template #footer>
        <div class="drawer-footer">
          <el-button
            v-if="selectedSource && selectedSource.document_id"
            type="primary"
            plain
            @click="handleDownloadOriginDoc"
          >
            <el-icon><Download /></el-icon> 下载原始文件
          </el-button>
          <el-button @click="sourceDrawerVisible = false">关闭</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { marked } from 'marked'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, ChatLineRound, EditPen, Delete, Download,
  DeleteFilled, ChatDotRound, Document, ArrowDown,
  ArrowUp, Files, Promotion, View, CopyDocument
} from '@element-plus/icons-vue'
import {
  getSessionsApi, createSessionApi, renameSessionApi,
  deleteSessionApi, clearSessionMessagesApi, getSessionMessagesApi,
  askQuestionApi, exportChatHistoryApi
} from '@/api/chat'
import { previewDocumentApi, downloadDocumentApi } from '@/api/document'

const sessions = ref([])
const currentSessionId = ref(null)
const messages = ref([])
const inputQuestion = ref('')
const sending = ref(false)
const messageBoxRef = ref(null)

const openedSources = reactive({})
const renameDialogVisible = ref(false)
const editingSessionId = ref(null)
const editTitle = ref('')

// 引用来源查看抽屉状态
const sourceDrawerVisible = ref(false)
const selectedSource = ref({})
const activeSourceTab = ref('chunk')
const docFullLoading = ref(false)
const docFullData = reactive({
  preview_text: '',
  total_chars: 0,
  total_pages: 0
})

const demoQuestions = [
  '员工每年的年休假有几天？',
  '公司员工考勤的弹性打卡时间是多久？',
  '公司一二线城市的出差住宿报销标准是多少？',
  '员工账号密码的安全复杂度规范是什么？',
  '内部研发代码是否可以上传到外部公开仓库？'
]

const renderMarkdown = (text) => {
  if (!text) return ''
  try {
    return marked.parse(text)
  } catch (e) {
    return text
  }
}

const formatTime = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const toggleSources = (msgId) => {
  openedSources[msgId] = !openedSources[msgId]
}

const handleOpenSourceDetail = async (src) => {
  selectedSource.value = { ...src }
  activeSourceTab.value = 'chunk'
  docFullData.preview_text = ''
  docFullData.total_chars = 0
  docFullData.total_pages = 0
  sourceDrawerVisible.value = true

  if (src.document_id) {
    loadFullDocument(src.document_id)
  }
}

const loadFullDocument = async (docId) => {
  if (docFullData.preview_text) return
  docFullLoading.value = true
  try {
    const res = await previewDocumentApi(docId)
    docFullData.preview_text = res.preview_text
    docFullData.total_chars = res.total_chars
    docFullData.total_pages = res.total_pages
  } catch (e) {
  } finally {
    docFullLoading.value = false
  }
}

const handleTabChange = (tabName) => {
  if (tabName === 'fullDoc' && selectedSource.value.document_id && !docFullData.preview_text) {
    loadFullDocument(selectedSource.value.document_id)
  }
}

const copyChunkContent = async () => {
  const text = selectedSource.value.content || selectedSource.value.content_preview || ''
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('切片内容已复制到剪贴板')
  } catch (e) {
    ElMessage.info('已选中文本，请使用 Ctrl+C 复制')
  }
}

const handleDownloadOriginDoc = async () => {
  const docId = selectedSource.value.document_id
  if (!docId) {
    ElMessage.warning('该记录无关联文档ID')
    return
  }
  try {
    const blob = await downloadDocumentApi(docId)
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', selectedSource.value.filename || '文档')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('原始文档已开始下载')
  } catch (e) {
    ElMessage.error('下载原始文档失败')
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageBoxRef.value) {
      messageBoxRef.value.scrollTop = messageBoxRef.value.scrollHeight
    }
  })
}

const fetchSessions = async () => {
  try {
    const list = await getSessionsApi()
    sessions.value = list
    if (list.length > 0 && !currentSessionId.value) {
      selectSession(list[0].id)
    }
  } catch (err) {}
}

const selectSession = async (sessionId) => {
  currentSessionId.value = sessionId
  try {
    const msgList = await getSessionMessagesApi(sessionId)
    messages.value = msgList
    scrollToBottom()
  } catch (err) {}
}

const handleCreateSession = async () => {
  try {
    const newSession = await createSessionApi({ title: '新对话' })
    sessions.value.unshift(newSession)
    currentSessionId.value = newSession.id
    messages.value = []
  } catch (err) {}
}

const openRenameDialog = (session) => {
  editingSessionId.value = session.id
  editTitle.value = session.title
  renameDialogVisible.value = true
}

const confirmRename = async () => {
  if (!editTitle.value.trim()) {
    ElMessage.warning('会话名称不能为空')
    return
  }
  try {
    await renameSessionApi(editingSessionId.value, { title: editTitle.value.trim() })
    const item = sessions.value.find(s => s.id === editingSessionId.value)
    if (item) item.title = editTitle.value.trim()
    renameDialogVisible.value = false
    ElMessage.success('会话重命名成功')
  } catch (err) {}
}

const handleDeleteSession = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该对话会话吗？', '确认删除', {
      type: 'warning'
    })
    await deleteSessionApi(id)
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (currentSessionId.value === id) {
      if (sessions.value.length > 0) {
        selectSession(sessions.value[0].id)
      } else {
        currentSessionId.value = null
        messages.value = []
      }
    }
    ElMessage.success('会话已删除')
  } catch (e) {}
}

const handleClearMessages = async () => {
  if (!currentSessionId.value) return
  try {
    await ElMessageBox.confirm('确定清空当前会话的全部记录吗？', '提示', { type: 'warning' })
    await clearSessionMessagesApi(currentSessionId.value)
    messages.value = []
    ElMessage.success('对话已清空')
  } catch (e) {}
}

const fillQuickQuestion = (q) => {
  inputQuestion.value = q
  handleSend()
}

const handleEnterSend = (e) => {
  if (e.shiftKey) {
    inputQuestion.value += '\n'
  } else {
    handleSend()
  }
}

const handleSend = async () => {
  const q = inputQuestion.value.trim()
  if (!q || sending.value) return

  inputQuestion.value = ''
  sending.value = true

  // 临时先放入 UI 列表
  const tempUserMsg = {
    id: Date.now(),
    role: 'user',
    content: q,
    created_at: new Date().toISOString()
  }
  messages.value.push(tempUserMsg)
  scrollToBottom()

  try {
    const res = await askQuestionApi({
      session_id: currentSessionId.value,
      content: q
    })

    if (!currentSessionId.value) {
      currentSessionId.value = res.session_id
      await fetchSessions()
    } else {
      // 刷新会话标题
      const s = sessions.value.find(item => item.id === res.session_id)
      if (s && s.title === '新对话') {
        s.title = q.substring(0, 20)
      }
    }

    // 压入 AI 回复
    const aiMsg = res.assistant_message
    messages.value.push(aiMsg)
    // 默认如果有关联来源，则默认展开最新一条
    if (aiMsg.sources && aiMsg.sources.length > 0) {
      openedSources[aiMsg.id] = true
    }
    scrollToBottom()
  } catch (err) {
    // 异常情况下删除临时提问或保留报错
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

const handleExportCsv = async () => {
  try {
    const blob = await exportChatHistoryApi(currentSessionId.value)
    const url = window.URL.createObjectURL(new Blob([blob], { type: 'text/csv;charset=utf-8;' }))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `企业知识库问答历史_${new Date().toISOString().slice(0, 10)}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    ElMessage.success('问答记录已成功导出为 CSV')
  } catch (e) {
    ElMessage.error('导出问答记录失败')
  }
}

onMounted(() => {
  fetchSessions()
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 92px);
  background-color: #ffffff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  border: 1px solid #e2e8f0;
}

/* 左侧会话边栏 */
.session-sidebar {
  width: 260px;
  background-color: #f8fafc;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 14px;
}

.new-chat-btn {
  width: 100%;
  font-weight: 500;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  color: #334155;
  font-size: 13px;
  gap: 8px;
}

.session-item:hover {
  background-color: #f1f5f9;
}

.session-item.active {
  background-color: #e0f2fe;
  color: #0284c7;
  font-weight: 600;
}

.session-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.session-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-actions {
  display: none;
  gap: 2px;
}

.session-item:hover .session-actions {
  display: flex;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* 右侧问答主面板 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
}

.message-stream {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 欢迎卡片 */
.welcome-card {
  text-align: center;
  max-width: 650px;
  margin: 40px auto;
  padding: 32px 24px;
  background: #f8fafc;
  border-radius: 16px;
  border: 1px dashed #cbd5e1;
}

.welcome-icon {
  margin-bottom: 12px;
}

.welcome-card h3 {
  font-size: 19px;
  color: #0f172a;
  margin-bottom: 8px;
}

.welcome-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 24px;
}

.quick-questions {
  text-align: left;
}

.quick-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 10px;
}

.question-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip-item {
  cursor: pointer;
  transition: all 0.2s;
  background-color: #ffffff;
  border-color: #cbd5e1;
  color: #334155;
}

.chip-item:hover {
  background-color: #eff6ff;
  border-color: #3b82f6;
  color: #2563eb;
}

/* 消息气泡行 */
.message-row {
  display: flex;
  gap: 12px;
  max-width: 85%;
}

.message-row.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-row.assistant {
  align-self: flex-start;
}

.user-avatar {
  background-color: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: bold;
}

.ai-avatar {
  background-color: #10b981;
  color: #fff;
  font-size: 13px;
  font-weight: bold;
}

.message-bubble-wrapper {
  display: flex;
  flex-direction: column;
}

.message-header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.message-row.user .message-header-info {
  justify-content: flex-end;
}

.bubble-content {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.message-row.user .bubble-content {
  background-color: #2563eb;
  color: #ffffff;
  border-bottom-right-radius: 2px;
}

.message-row.assistant .bubble-content {
  background-color: #f1f5f9;
  color: #1e293b;
  border-bottom-left-radius: 2px;
}

.thinking-bubble {
  color: #64748b;
  font-style: italic;
}

/* 引用来源卡片 */
.sources-card {
  margin-top: 8px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  font-size: 12px;
}

.sources-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background-color: #edf2f7;
  color: #475569;
  cursor: pointer;
  font-weight: 500;
  user-select: none;
}

.sources-toggle:hover {
  background-color: #e2e8f0;
}

.arrow-icon {
  margin-left: auto;
}

.sources-list {
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-item {
  padding: 10px 12px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #edf2f7;
  transition: all 0.2s ease;
}

.source-item.clickable {
  cursor: pointer;
}

.source-item.clickable:hover {
  border-color: #3b82f6;
  background-color: #f8faff;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
  transform: translateY(-1px);
}

.source-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.source-doc-name {
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 4px;
}

.source-action-pill {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #2563eb;
  font-weight: 500;
  background: #eff6ff;
  padding: 2px 8px;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.source-item:hover .source-action-pill {
  background: #2563eb;
  color: #ffffff;
}

.source-preview {
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

/* 抽屉样式 */
.drawer-source-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.source-meta-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.meta-tag-item {
  display: flex;
  align-items: center;
  font-size: 13px;
}

.meta-label {
  color: #64748b;
  margin-right: 4px;
}

.source-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chunk-content-box, .full-doc-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.box-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #64748b;
  padding: 4px 0;
}

.chunk-text-view {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 16px;
  font-size: 13.5px;
  line-height: 1.8;
  color: #0f172a;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 520px;
  overflow-y: auto;
}

.full-doc-text-view {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  max-height: 520px;
  overflow-y: auto;
}

.full-doc-text-view pre {
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.7;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-all;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 底部输入框 */
.input-panel {
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  background-color: #ffffff;
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.hint-text {
  font-size: 12px;
  color: #94a3b8;
}
</style>
