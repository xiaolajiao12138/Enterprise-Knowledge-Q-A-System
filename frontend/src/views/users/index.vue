<template>
  <div class="users-container">
    <el-card shadow="never" class="user-card">
      <template #header>
        <div class="card-header">
          <div>
            <span class="header-title">企业用户权限管理</span>
            <span class="header-desc">管理员可新增员工账号、调整角色权限及重置登录密码</span>
          </div>
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>
            新增用户
          </el-button>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="用户ID" width="90" align="center" />

        <el-table-column prop="username" label="用户名" min-width="140">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="26" class="table-avatar">
                {{ row.username.substring(0, 1).toUpperCase() }}
              </el-avatar>
              <span class="username-text">{{ row.username }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="系统角色" width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" effect="light">
              {{ row.role === 'admin' ? '系统管理员' : '普通员工' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="账号状态" width="130" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              inline-prompt
              active-text="启用"
              inactive-text="禁用"
              :disabled="row.id === userStore.user?.id"
              @change="(val) => handleToggleStatus(row, val)"
            />
          </template>
        </el-table-column>

        <el-table-column label="注册时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openResetDialog(row)">
              <el-icon><Key /></el-icon>
              重置密码
            </el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="row.id === userStore.user?.id"
              @click="handleDeleteUser(row)"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增用户 Dialog -->
    <el-dialog v-model="createDialogVisible" title="新增系统用户" width="460px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="请输入员工用户名" />
        </el-form-item>
        <el-form-item label="初始密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password placeholder="至少 6 位字符" />
        </el-form-item>
        <el-form-item label="分配角色" prop="role">
          <el-radio-group v-model="createForm.role">
            <el-radio value="employee">普通员工 (仅问答)</el-radio>
            <el-radio value="admin">系统管理员 (全权)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="启用账号">
          <el-switch v-model="createForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitCreateUser">
          确认创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 Dialog -->
    <el-dialog v-model="resetDialogVisible" :title="`重置用户 [${targetUser?.username}] 的密码`" width="420px">
      <el-form ref="resetFormRef" :model="resetForm" :rules="resetRules" label-width="90px">
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="resetForm.new_password" type="password" show-password placeholder="请输入新的登录密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitResetPassword">
          确认重置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/store/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Key, Delete } from '@element-plus/icons-vue'
import {
  getUsersApi, createUserApi, updateUserApi,
  resetPasswordApi, deleteUserApi
} from '@/api/user'

const userStore = useUserStore()
const users = ref([])
const loading = ref(false)
const submitLoading = ref(false)

const createDialogVisible = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  username: '',
  password: '',
  role: 'employee',
  is_active: true
})
const createRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码不能少于 6 位', trigger: 'blur' }]
}

const resetDialogVisible = ref(false)
const resetFormRef = ref(null)
const targetUser = ref(null)
const resetForm = reactive({ new_password: '' })
const resetRules = {
  new_password: [{ required: true, min: 6, message: '新密码不能少于 6 位', trigger: 'blur' }]
}

const formatDateTime = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleString()
}

const fetchUsers = async () => {
  loading.value = true
  try {
    const list = await getUsersApi()
    users.value = list
  } catch (e) {
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  createForm.username = ''
  createForm.password = ''
  createForm.role = 'employee'
  createForm.is_active = true
  createDialogVisible.value = true
}

const submitCreateUser = async () => {
  if (!createFormRef.value) return
  await createFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      await createUserApi(createForm)
      ElMessage.success(`用户 [${createForm.username}] 创建成功`)
      createDialogVisible.value = false
      fetchUsers()
    } catch (e) {
    } finally {
      submitLoading.value = false
    }
  })
}

const handleToggleStatus = async (row, val) => {
  try {
    await updateUserApi(row.id, { is_active: val })
    ElMessage.success(`用户 [${row.username}] 状态已${val ? '启用' : '禁用'}`)
  } catch (e) {
    row.is_active = !val
  }
}

const openResetDialog = (row) => {
  targetUser.value = row
  resetForm.new_password = ''
  resetDialogVisible.value = true
}

const submitResetPassword = async () => {
  if (!resetFormRef.value) return
  await resetFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      await resetPasswordApi(targetUser.value.id, resetForm)
      ElMessage.success(`用户 [${targetUser.value.username}] 密码重置成功`)
      resetDialogVisible.value = false
    } catch (e) {
    } finally {
      submitLoading.value = false
    }
  })
}

const handleDeleteUser = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要彻底删除用户 [${row.username}] 吗？`, '警告', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    })
    await deleteUserApi(row.id)
    ElMessage.success('用户删除成功')
    fetchUsers()
  } catch (e) {}
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.users-container {
  display: flex;
  flex-direction: column;
}

.user-card {
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.header-desc {
  font-size: 12px;
  color: #64748b;
  margin-left: 12px;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-avatar {
  background-color: #3b82f6;
  color: #fff;
  font-size: 11px;
}

.username-text {
  font-weight: 500;
  color: #1e293b;
}
</style>
