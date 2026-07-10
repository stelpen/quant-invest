<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: 'admin',
  password: 'admin123',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.replace(redirect)
  } catch {
    // 拦截器已展示错误
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-bg" />
    <el-card class="login-card" shadow="always">
      <div class="login-header">
        <h1>量化投资工具</h1>
        <p>A 股智能投研平台</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="onSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="密码" :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" style="width: 100%" @click="onSubmit">登 录</el-button>
        </el-form-item>
      </el-form>
      <div class="login-tip">
        <el-alert type="info" :closable="false" show-icon>
          <template #title>
            演示账号：<b>admin</b> / 密码：<b>admin123</b>
          </template>
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  overflow: hidden;
}
.login-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 20% 30%, rgba(255, 255, 255, 0.08), transparent 40%),
    radial-gradient(circle at 80% 70%, rgba(255, 255, 255, 0.06), transparent 40%);
}
.login-card {
  position: relative;
  width: 380px;
  border-radius: 12px;
  z-index: 1;
}
.login-header {
  text-align: center;
  margin-bottom: 24px;
}
.login-header h1 {
  margin: 0;
  font-size: 22px;
  color: #303133;
}
.login-header p {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}
.login-tip {
  margin-top: 8px;
}
</style>
