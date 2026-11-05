<template>
  <div class="knowledge-container">
    <!-- 顶部概览数据卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">知识库文档总数</span>
              <span class="stat-value">{{ documents.length }}</span>
            </div>
            <div class="stat-icon-wrapper blue">
              <el-icon :size="24"><Files /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">Chroma 向量切片总数</span>
              <span class="stat-value">{{ chromaStats.total_vectors || 0 }}</span>
            </div>
            <div class="stat-icon-wrapper green">
              <el-icon :size="24"><Collection /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">向量库操作</span>
              <div class="stat-ops">
                <el-button size="small" type="danger" plain @click="handleClearChroma">
                  <el-icon><Delete /></el-icon>
                  清空全部向量
                </el-button>
              </div>
            </div>
            <div class="stat-icon-wrapper red">
              <el-icon :size="24"><Coin /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 文档上传卡片 -->
    <el-card shadow="never" class="section-card upload-card">
      <template #header>
        <div class="card-header">
          <span class="header-title">上传企业文档</span>
          <span class="header-tip">单文件最大 20MB，支持格式：.pdf, .docx, .txt, .md</span>
        </div>
      </template>

      <el-upload
        class="doc-uploader"
        drag
        action="#"
        :http-request="customUpload"
        :show-file-list="false"
        :before-upload="beforeUpload"
      >
        <el-icon class="el-icon--upload" :size="48"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将企业文档拖拽至此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            系统将自动在后台进行多线程文本提取、分段切片（Chunking）与向量嵌入入库。
          </div>
        </template>
      </el-upload>
    </el-card>

    <!-- 文档列表卡片 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span class="header-title">知识库文档列表</span>
          <el-button size="small" @click="refreshData">
            <el-icon><Refresh /></el-icon>
            刷新列表
          </el-button>
        </div>
      </template>

      <el-table :data="documents" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" align="center" />

        <el-table-column label="文档名称" min-width="220">
          <template #default="{ row }">
            <div class="doc-name-cell">
              <el-icon class="doc-type-icon"><Document /></el-icon>
              <span class="doc-title" :title="row.filename">{{ row.filename }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="格式" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.file_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="文件大小" width="110" align="right">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>

        <el-table-column prop="chunk_count" label="切片数" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.chunk_count }} 个</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'completed'" type="success" size="small">解析成功</el-tag>
            <el-tag v-else-if="row.status === 'processing'" type="warning" size="small">
              <el-icon class="is-loading"><Loading /></el-icon>
              切片处理中
            </el-tag>
            <el-tooltip v-else-if="row.status === 'failed'" :content="row.error_msg || '处理失败'" placement="top">
              <el-tag type="danger" size="small">解析失败</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="上传时间" width="170" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handlePreview(row)">
              <el-icon><View /></el-icon>
              预览
            </el-button>
            <el-button link type="warning" size="small" @click="handleReindex(row)">
              <el-icon><RefreshRight /></el-icon>
              重向量化
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 文档内容预览 Drawer -->
    <el-drawer
      v-model="previewDrawerVisible"
      :title="`文档解析预览: ${previewData.filename}`"
      size="50%"
      destroy-on-close
    >
      <div v-loading="previewLoading" class="preview-container">
        <div class="preview-meta">
          <span>总字符数: <strong>{{ previewData.total_chars }}</strong></span>
          <span>总页数/段落数: <strong>{{ previewData.total_pages }}</strong></span>
        </div>
        <el-divider />
        <pre class="preview-text-block">{{ previewData.preview_text }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Files, Collection, Delete, Coin, UploadFilled,
  Refresh, Document, Loading, View, RefreshRight
} from '@element-plus/icons-vue'
import {
  getDocumentsApi, uploadDocumentApi, previewDocumentApi,
  deleteDocumentApi, reindexDocumentApi, getChromaStatsApi, clearChromaApi
} from '@/api/document'

const documents = ref([])
const loading = ref(false)
const chromaStats = reactive({ total_vectors: 0 })

const previewDrawerVisible = ref(false)
const previewLoading = ref(false)
const previewData = reactive({
  filename: '',
  preview_text: '',
  total_chars: 0,
  total_pages: 0
})

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDateTime = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleString()
}

const fetchDocuments = async () => {
  loading.value = true
  try {
    const list = await getDocumentsApi()
    documents.value = list
  } catch (err) {
  } finally {
    loading.value = false
  }
}

const fetchChromaStats = async () => {
  try {
    const stats = await getChromaStatsApi()
    chromaStats.total_vectors = stats.total_vectors
  } catch (err) {}
}

const refreshData = () => {
  fetchDocuments()
  fetchChromaStats()
}

const beforeUpload = (file) => {
  const allowed = ['.pdf', '.docx', '.txt', '.md']
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
  if (!allowed.includes(ext)) {
    ElMessage.error(`不支持的文件格式，仅支持: ${allowed.join(', ')}`)
    return false
  }
  const isLt20M = file.size / 1024 / 1024 <= 20
  if (!isLt20M) {
    ElMessage.error('上传文件大小不能超过 20MB!')
    return false
  }
  return true
}

const customUpload = async (options) => {
  const { file } = options
  const formData = new FormData()
  formData.append('file', file)

  try {
    await uploadDocumentApi(formData)
    ElMessage.success(`文档 [${file.name}] 已上传，正在后台异步切片与向量化`)
    refreshData()
    // 轮询几次更新解析状态
    setTimeout(refreshData, 3000)
    setTimeout(refreshData, 8000)
  } catch (e) {}
}

const handlePreview = async (row) => {
  previewDrawerVisible.value = true
  previewLoading.value = true
  previewData.filename = row.filename
  previewData.preview_text = ''
  try {
    const res = await previewDocumentApi(row.id)
    previewData.preview_text = res.preview_text
    previewData.total_chars = res.total_chars
    previewData.total_pages = res.total_pages
  } catch (e) {
  } finally {
    previewLoading.value = false
  }
}

const handleReindex = async (row) => {
  try {
    await reindexDocumentApi(row.id)
    ElMessage.success(`已为文档 [${row.filename}] 提交重新切片向量化任务`)
    refreshData()
    setTimeout(refreshData, 4000)
  } catch (e) {}
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除文档 [${row.filename}] 及其向量数据吗？`, '危险操作确认', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    })
    await deleteDocumentApi(row.id)
    ElMessage.success('文档及其向量已成功删除')
    refreshData()
  } catch (e) {}
}

const handleClearChroma = async () => {
  try {
    await ElMessageBox.confirm('清空向量库将移除 Chroma 中的所有向量切片数据，确定继续吗？', '严重警告', {
      type: 'error',
      confirmButtonText: '清空向量库',
      cancelButtonText: '取消'
    })
    await clearChromaApi()
    ElMessage.success('已清空全部向量库')
    refreshData()
  } catch (e) {}
}

onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.knowledge-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-row {
  margin-bottom: 4px;
}

.stat-card {
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.stat-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 13px;
  color: #64748b;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}

.stat-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon-wrapper.blue {
  background-color: #eff6ff;
  color: #2563eb;
}

.stat-icon-wrapper.green {
  background-color: #ecfdf5;
  color: #059669;
}

.stat-icon-wrapper.red {
  background-color: #fef2f2;
  color: #dc2626;
}

.section-card {
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.header-tip {
  font-size: 12px;
  color: #94a3b8;
}

.doc-uploader :deep(.el-upload-dragger) {
  padding: 24px;
  border-radius: 10px;
}

.doc-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-type-icon {
  color: #3b82f6;
  font-size: 16px;
}

.doc-title {
  font-weight: 500;
  color: #1e293b;
}

.preview-container {
  padding: 0 8px;
}

.preview-meta {
  display: flex;
  gap: 24px;
  font-size: 13px;
  color: #475569;
}

.preview-text-block {
  background: #f8fafc;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  max-height: 70vh;
  overflow-y: auto;
}
</style>
