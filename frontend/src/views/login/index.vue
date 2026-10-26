<template>
  <div class="login-page">
    <div class="login-page__decor login-page__decor--one" aria-hidden="true"></div>
    <div class="login-page__decor login-page__decor--two" aria-hidden="true"></div>

    <el-card class="login-card" shadow="always">
      <div class="login-card__header">
        <div class="login-logo">
          <el-icon :size="30"><Van /></el-icon>
        </div>
        <h1 class="login-title">{{ appTitle }}</h1>
        <p class="login-subtitle">配件库存 · 出入库 · 扫码盘点</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @keyup.enter="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            :prefix-icon="User"
            placeholder="请输入用户名"
            autocomplete="username"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            :prefix-icon="Lock"
            placeholder="请输入密码"
            autocomplete="current-password"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          class="login-button"
          :loading="loading"
          @click="handleLogin"
        >
          {{ loading ? '登录中...' : '登 录' }}
        </el-button>
      </el-form>

      <p class="login-footer">© {{ currentYear }} 车队配件库存管理系统</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'

import { Lock, User, Van } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { useUserStore } from '@/stores/user'

interface LoginForm {
  username: string
  password: string
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const appTitle = import.meta.env.VITE_APP_TITLE || '车队配件库存管理系统'
const currentYear = new Date().getFullYear()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive<LoginForm>({
  username: '',
  password: ''
})

const rules: FormRules<LoginForm> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '用户名长度为 2 ~ 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码长度为 6 ~ 128 个字符', trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!formRef.value || loading.value) {
    return
  }

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  loading.value = true
  try {
    await userStore.login({ ...form })
    ElMessage.success('登录成功')

    const redirectQuery = route.query.redirect
    const redirect =
      typeof redirectQuery === 'string' &&
      redirectQuery.startsWith('/') &&
      !redirectQuery.startsWith('//')
        ? redirectQuery
        : '/dashboard'

    await router.replace(redirect)
  } catch {
    // 业务错误提示已由 request.ts 响应拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-page {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
  overflow: hidden;
  background: linear-gradient(135deg, #1f2d3d 0%, #2b5876 55%, #4e4376 100%);
}

.login-page__decor {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  filter: blur(2px);

  &--one {
    top: -140px;
    left: -120px;
    width: 420px;
    height: 420px;
  }

  &--two {
    right: -100px;
    bottom: -120px;
    width: 360px;
    height: 360px;
  }
}

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  border: none;
  border-radius: 12px;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.28);

  :deep(.el-card__body) {
    padding: 36px 32px 28px;
  }
}

.login-card__header {
  margin-bottom: 24px;
  text-align: center;
}

.login-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  color: #fff;
  background: linear-gradient(135deg, #409eff 0%, #2b5876 100%);
  border-radius: 14px;
}

.login-title {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.login-subtitle {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.login-button {
  width: 100%;
  margin-top: 8px;
  letter-spacing: 2px;
}

.login-footer {
  margin: 20px 0 0;
  font-size: 12px;
  color: #c0c4cc;
  text-align: center;
}

@media (max-width: 480px) {
  .login-card {
    :deep(.el-card__body) {
      padding: 28px 20px 22px;
    }
  }

  .login-title {
    font-size: 18px;
  }
}
</style>

