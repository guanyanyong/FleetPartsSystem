<template>
  <el-input
    ref="inputRef"
    v-model="value"
    :placeholder="placeholder"
    :disabled="disabled"
    :clearable="false"
    class="scan-input"
    @keyup.enter="handleEnter"
  >
    <template #prefix>
      <el-icon><Aim /></el-icon>
    </template>
  </el-input>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { Aim } from '@element-plus/icons-vue'
import type { InputInstance } from 'element-plus'

/**
 * 扫码输入框：扫码枪以「键盘输入 + 回车」方式工作。
 * 回车后触发 scan 事件并清空输入框，同时保持焦点，便于连续扫码。
 */
interface Props {
  placeholder?: string
  /** 是否禁用输入（如提交中） */
  disabled?: boolean
  /** 是否在挂载后自动聚焦 */
  autoFocus?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '扫描条码 / 二维码后按回车',
  disabled: false,
  autoFocus: true
})

const emit = defineEmits<{
  (event: 'scan', code: string): void
}>()

const value = ref('')
const inputRef = ref<InputInstance>()

function focus() {
  inputRef.value?.focus()
}

function handleEnter() {
  const code = value.value.trim()
  if (!code) {
    return
  }
  value.value = ''
  emit('scan', code)
  // 扫码枪连续扫描时保持焦点
  focus()
}

onMounted(() => {
  if (props.autoFocus) {
    focus()
  }
})

defineExpose({ focus })
</script>

<style scoped>
.scan-input {
  width: 100%;
}

.scan-input :deep(.el-input__inner) {
  font-family: Consolas, Monaco, 'Courier New', monospace;
  letter-spacing: 0.02em;
}
</style>
