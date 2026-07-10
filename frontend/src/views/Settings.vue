<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Bell, Notification, Lock } from '@element-plus/icons-vue'
import { syncStatus, syncData, type SyncStatusResp } from '@/api/data'
import { testNotify } from '@/api/signals'
import http from '@/api/index'

const tab = ref('data')

const syncInfo = ref<SyncStatusResp | null>(null)
const syncing = ref(false)
const testing = ref(false)

const notif = reactive({
  webhook_url: '',
  email: '',
  enabled_webhook: true,
  enabled_email: false,
})

const strategies = ref<Array<{ key: string; name: string; enabled: boolean; description?: string }>>([
  { key: 'ma_cross', name: '双均线交叉', enabled: true, description: '快慢均线金叉死叉信号' },
  { key: 'macd', name: 'MACD', enabled: true, description: 'MACD 金叉死叉' },
  { key: 'rsi', name: 'RSI 超买超卖', enabled: false, description: 'RSI 阈值突破' },
  { key: 'breakout', name: '突破策略', enabled: true, description: 'N 日新高突破' },
])

const pwd = reactive({ old: '', new: '', confirm: '' })

async function loadSync() {
  try {
    syncInfo.value = await syncStatus()
  } catch {
    // ignored
  }
}

async function onSync() {
  syncing.value = true
  try {
    await syncData()
    ElMessage.success('同步已触发')
    await loadSync()
  } catch {
    // ignored
  } finally {
    syncing.value = false
  }
}

async function onTestNotify() {
  testing.value = true
  try {
    const r = await testNotify()
    if (r?.ok) ElMessage.success('测试通知已发送')
    else ElMessage.warning(r?.message || '通知未发送')
  } catch {
    // ignored
  } finally {
    testing.value = false
  }
}

function onSaveNotif() {
  ElMessage.success('通知设置已保存（本地）')
}

function onChangePassword() {
  if (!pwd.old || !pwd.new) {
    ElMessage.warning('请填写完整')
    return
  }
  if (pwd.new !== pwd.confirm) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }
  // 实际请求取决于后端接口
  http
    .post('/auth/change-password', { old_password: pwd.old, new_password: pwd.new })
    .then(() => {
      ElMessage.success('密码修改成功')
      pwd.old = pwd.new = pwd.confirm = ''
    })
    .catch(() => {
      // interceptor 显示错误
    })
}

onMounted(loadSync)
</script>

<template>
  <el-tabs v-model="tab" type="border-card" class="settings-tabs">
    <!-- 数据同步 -->
    <el-tab-pane label="数据同步" name="data">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="状态">{{ syncInfo?.status || '--' }}</el-descriptions-item>
        <el-descriptions-item label="上次运行">{{ syncInfo?.last_run || '--' }}</el-descriptions-item>
        <el-descriptions-item label="进度">{{ (syncInfo?.progress ?? 0) + '%' }}</el-descriptions-item>
        <el-descriptions-item label="消息">{{ syncInfo?.message || '--' }}</el-descriptions-item>
      </el-descriptions>
      <div class="row">
        <el-button type="primary" :icon="Refresh" :loading="syncing" @click="onSync">手动同步</el-button>
        <el-button @click="loadSync">刷新状态</el-button>
      </div>
    </el-tab-pane>

    <!-- 通知设置 -->
    <el-tab-pane label="通知设置" name="notif">
      <el-form :model="notif" label-width="120px" style="max-width: 560px">
        <el-form-item label="启用 Webhook">
          <el-switch v-model="notif.enabled_webhook" />
        </el-form-item>
        <el-form-item label="Webhook URL">
          <el-input v-model="notif.webhook_url" placeholder="https://example.com/webhook" />
        </el-form-item>
        <el-form-item label="启用邮件">
          <el-switch v-model="notif.enabled_email" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="notif.email" placeholder="user@example.com" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Notification" :loading="testing" @click="onTestNotify">发送测试通知</el-button>
          <el-button :icon="Bell" @click="onSaveNotif">保存设置</el-button>
        </el-form-item>
      </el-form>
    </el-tab-pane>

    <!-- 策略 -->
    <el-tab-pane label="策略" name="strategies">
      <el-table :data="strategies" stripe>
        <el-table-column prop="name" label="策略" width="180" />
        <el-table-column prop="description" label="说明" min-width="240" />
        <el-table-column label="启用" width="100" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" />
          </template>
        </el-table-column>
      </el-table>
      <div class="row">
        <el-button type="primary" @click="ElMessage.success('策略设置已保存（本地）')">保存</el-button>
      </div>
    </el-tab-pane>

    <!-- 账户 -->
    <el-tab-pane label="账户" name="account">
      <el-form :model="pwd" label-width="120px" style="max-width: 480px">
        <el-form-item label="原密码">
          <el-input v-model="pwd.old" type="password" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwd.new" type="password" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="pwd.confirm" type="password" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onChangePassword">修改密码</el-button>
        </el-form-item>
      </el-form>
    </el-tab-pane>
  </el-tabs>
</template>

<style scoped>
.settings-tabs {
  background: #fff;
}
.row {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
</style>
