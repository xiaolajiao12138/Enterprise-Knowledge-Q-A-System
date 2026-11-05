<template>
  <div class="settings-container">
    <el-card shadow="never" class="settings-card">
      <el-tabs v-model="activeTab">
        <!-- 标签页 1: 参数配置 -->
        <el-tab-pane label="大模型与知识库配置" name="config">
          <div class="tab-body">
            <el-form
              ref="configFormRef"
              :model="form"
              label-position="top"
              class="config-form"
            >
              <!-- 大模型 (LLM) 配置区 -->
              <div class="form-section-title">
                <el-icon><Cpu /></el-icon>
                <span>大语言模型 (LLM) 推理配置</span>
              </div>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="模型服务提供商">
                    <el-select v-model="form.llm_provider" style="width: 100%">
                      <el-option label="OpenAI 兼容第三方接口 (推荐，支持中转站/DeepSeek/通义千问)" value="openai" />
                      <el-option label="本地私有化部署 (Ollama)" value="ollama" />
                    </el-select>
                  </el-form-item>
                </el-col>

                <el-col :span="12">
                  <el-form-item label="API 服务基地址 (Base URL)">
                    <el-input v-model="form.llm_base_url" placeholder="如 https://api.openai.com/v1 或 http://127.0.0.1:11434" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="API Key (密钥)">
                    <el-input v-model="form.llm_api_key" type="password" show-password placeholder="第三方中转站填入 sk-xxx，本地 Ollama 填 EMPTY" />
                  </el-form-item>
                </el-col>

                <el-col :span="12">
                  <el-form-item label="推理模型标识 (Model Name)">
                    <el-input v-model="form.llm_model" placeholder="如 gpt-4o-mini, gpt-6.1-sol, deepseek-chat, qwen2:7b" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="温度 (Temperature，越低越严谨)">
                    <el-slider v-model="form.temperature" :min="0" :max="1" :step="0.05" show-input />
                  </el-form-item>
                </el-col>

                <el-col :span="8">
                  <el-form-item label="Top-P 采样阈值">
                    <el-slider v-model="form.top_p" :min="0.1" :max="1" :step="0.05" show-input />
                  </el-form-item>
                </el-col>

                <el-col :span="8">
                  <el-form-item label="知识库检索引用片段数 (Top-K)">
                    <el-input-number v-model="form.top_k" :min="1" :max="10" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>

              <!-- 连通性测试栏 -->
              <div class="test-bar">
                <el-button type="info" plain :loading="testing" @click="handleTestConnection">
                  <el-icon><Connection /></el-icon>
                  测试大模型接口连通性
                </el-button>
                <span v-if="testResult" :class="['test-badge', testResult.status]">
                  {{ testResult.message }}
                </span>
              </div>

              <el-divider />

              <!-- 向量与切片配置区 -->
              <div class="form-section-title">
                <el-icon><Files /></el-icon>
                <span>文本切片与向量 Embedding 配置</span>
              </div>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="向量检索提供商 (Embedding Provider)">
                    <el-select v-model="form.embedding_provider" style="width: 100%">
                      <el-option label="内置分词与向量引擎 (推荐，免安装任何本地软件，开箱即用)" value="builtin" />
                      <el-option label="本地私有化部署 (Ollama 11434)" value="ollama" />
                      <el-option label="OpenAI 兼容第三方 Embedding 接口" value="openai" />
                    </el-select>
                  </el-form-item>
                </el-col>

                <el-col :span="12">
                  <div class="provider-tip-box">
                    <el-alert
                      v-if="form.embedding_provider === 'builtin'"
                      title="推荐模式：已开启内置高精度分词与跳字模糊匹配，无需在电脑安装配置 Ollama 即可快速运行！"
                      type="success"
                      :closable="false"
                      show-icon
                    />
                    <el-alert
                      v-else-if="form.embedding_provider === 'ollama'"
                      title="本地模式：需下载并运行 Ollama，执行 `ollama pull nomic-embed-text` 拉取向量模型。"
                      type="warning"
                      :closable="false"
                      show-icon
                    />
                    <el-alert
                      v-else
                      title="第三方 API 模式：需您的第三方账号支持 `text-embedding-3-small` 等向量接口。"
                      type="info"
                      :closable="false"
                      show-icon
                    />
                  </div>
                </el-col>
              </el-row>

              <el-row :gutter="20" v-if="form.embedding_provider !== 'builtin'">
                <el-col :span="12">
                  <el-form-item label="Embedding 模型标识">
                    <el-input v-model="form.embedding_model" placeholder="如 nomic-embed-text 或 text-embedding-3-small" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="Embedding 服务地址">
                    <el-input v-model="form.embedding_base_url" placeholder="如 http://127.0.0.1:11434 或 https://api.openai.com/v1" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="文档分块大小 (Chunk Size，建议 300-800)">
                    <el-input-number v-model="form.chunk_size" :min="100" :max="2000" :step="50" style="width: 100%" />
                  </el-form-item>
                </el-col>

                <el-col :span="12">
                  <el-form-item label="分块重叠长度 (Chunk Overlap，建议 30-100)">
                    <el-input-number v-model="form.chunk_overlap" :min="0" :max="500" :step="10" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>

              <div class="submit-footer">
                <el-button type="primary" size="large" :loading="saving" @click="handleSaveConfig">
                  <el-icon><Check /></el-icon>
                  保存系统配置
                </el-button>
              </div>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- 标签页 2: 日志查看 -->
        <el-tab-pane label="系统运行与文档日志" name="logs">
          <div class="tab-body">
            <div class="filter-bar">
              <el-select v-model="logQuery.module" placeholder="全部模块" clearable style="width: 140px">
                <el-option label="认证 (AUTH)" value="AUTH" />
                <el-option label="文档 (DOC)" value="DOC" />
                <el-option label="问答 (CHAT)" value="CHAT" />
                <el-option label="系统 (SYSTEM)" value="SYSTEM" />
              </el-select>

              <el-select v-model="logQuery.level" placeholder="全部级别" clearable style="width: 140px">
                <el-option label="INFO" value="INFO" />
                <el-option label="WARNING" value="WARNING" />
                <el-option label="ERROR" value="ERROR" />
              </el-select>

              <el-button type="primary" plain @click="fetchLogs">
                <el-icon><Search /></el-icon>
                查询
              </el-button>
              <el-button @click="resetLogFilter">重置</el-button>
            </div>

            <el-table :data="logs" v-loading="logLoading" stripe style="width: 100%; margin-top: 14px">
              <el-table-column prop="id" label="ID" width="70" align="center" />
              <el-table-column label="产生时间" width="170" align="center">
                <template #default="{ row }">
                  {{ formatDateTime(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column prop="module" label="模块" width="100" align="center">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ row.module }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="level" label="级别" width="90" align="center">
                <template #default="{ row }">
                  <el-tag
                    :type="row.level === 'ERROR' ? 'danger' : row.level === 'WARNING' ? 'warning' : 'success'"
                    size="small"
                  >
                    {{ row.level }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="operator" label="操作人" width="110" align="center" />
              <el-table-column prop="message" label="日志简短说明" min-width="260" show-overflow-tooltip />
              <el-table-column label="详情" width="90" align="center">
                <template #default="{ row }">
                  <el-button v-if="row.details" link type="primary" size="small" @click="viewLogDetail(row)">
                    查看
                  </el-button>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-box">
              <el-pagination
                v-model:current-page="logQuery.page"
                v-model:page-size="logQuery.page_size"
                :total="logTotal"
                layout="total, prev, pager, next"
                @current-change="fetchLogs"
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 日志详情弹窗 -->
    <el-dialog v-model="detailDialogVisible" title="日志详情堆栈" width="600px">
      <pre class="log-detail-pre">{{ activeDetail }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu, Connection, Files, Check, Search } from '@element-plus/icons-vue'
import {
  getSystemConfigApi, updateSystemConfigApi,
  testModelConnectionApi, getSystemLogsApi
} from '@/api/setting'

const activeTab = ref('config')

const form = reactive({
  llm_provider: 'openai',
  llm_base_url: 'https://sub2api.starysp.top/v1',
  llm_api_key: '',
  llm_model: 'gpt-6.1-sol',
  temperature: 0.1,
  top_p: 0.8,
  top_k: 4,
  embedding_provider: 'builtin',
  embedding_base_url: 'http://127.0.0.1:11434',
  embedding_api_key: 'EMPTY',
  embedding_model: 'nomic-embed-text',
  chunk_size: 500,
  chunk_overlap: 50
})

const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

// 日志状态
const logs = ref([])
const logTotal = ref(0)
const logLoading = ref(false)
const logQuery = reactive({
  module: '',
  level: '',
  page: 1,
  page_size: 15
})

const detailDialogVisible = ref(false)
const activeDetail = ref('')

const formatDateTime = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleString()
}

const fetchConfig = async () => {
  try {
    const res = await getSystemConfigApi()
    Object.assign(form, res)
  } catch (e) {}
}

const handleTestConnection = async () => {
  testing.value = true
  testResult.value = null
  try {
    const res = await testModelConnectionApi({
      provider: form.llm_provider,
      base_url: form.llm_base_url,
      api_key: form.llm_api_key,
      model: form.llm_model
    })
    testResult.value = res
  } catch (e) {
    testResult.value = { status: 'error', message: '连接测试失败: ' + e.message }
  } finally {
    testing.value = false
  }
}

const handleSaveConfig = async () => {
  saving.value = true
  try {
    await updateSystemConfigApi(form)
    ElMessage.success('系统参数配置已保存生效')
  } catch (e) {
  } finally {
    saving.value = false
  }
}

const fetchLogs = async () => {
  logLoading.value = true
  try {
    const res = await getSystemLogsApi(logQuery)
    logs.value = res.items
    logTotal.value = res.total
  } catch (e) {
  } finally {
    logLoading.value = false
  }
}

const resetLogFilter = () => {
  logQuery.module = ''
  logQuery.level = ''
  logQuery.page = 1
  fetchLogs()
}

const viewLogDetail = (row) => {
  activeDetail.value = row.details || '无详细堆栈'
  detailDialogVisible.value = true
}

onMounted(() => {
  fetchConfig()
  fetchLogs()
})
</script>

<style scoped>
.settings-container {
  display: flex;
  flex-direction: column;
}

.settings-card {
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.tab-body {
  padding: 10px 0;
}

.form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin: 10px 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #e2e8f0;
}

.test-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 10px;
}

.test-badge {
  font-size: 13px;
  padding: 4px 12px;
  border-radius: 6px;
}

.test-badge.success {
  background-color: #ecfdf5;
  color: #059669;
}

.test-badge.error {
  background-color: #fef2f2;
  color: #dc2626;
}

.provider-tip-box {
  margin-top: 30px;
}

.submit-footer {
  margin-top: 24px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pagination-box {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.log-detail-pre {
  background: #f8fafc;
  padding: 14px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  max-height: 400px;
  overflow-y: auto;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.text-muted {
  color: #94a3b8;
}
</style>
