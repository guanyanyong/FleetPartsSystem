<template>
  <canvas ref="canvasRef" class="qr-code" />
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import QRCode from 'qrcode'

/** 二维码生成组件：value 为空时渲染空白画布 */
const props = withDefaults(
  defineProps<{
    /** 二维码内容 */
    value: string
    /** 画布边长（px） */
    size?: number
  }>(),
  { size: 150 }
)

const canvasRef = ref<HTMLCanvasElement>()
const dataUrl = ref('')
const errorMessage = ref('')

async function render() {
  const canvas = canvasRef.value
  if (!canvas) {
    return
  }

  if (!props.value) {
    canvas.width = props.size
    canvas.height = props.size
    canvas.getContext('2d')?.clearRect(0, 0, props.size, props.size)
    dataUrl.value = ''
    errorMessage.value = ''
    return
  }

  try {
    await QRCode.toCanvas(canvas, props.value, {
      width: props.size,
      margin: 1,
      color: { dark: '#000000', light: '#ffffff' }
    })
    dataUrl.value = canvas.toDataURL('image/png')
    errorMessage.value = ''
  } catch {
    // 内容过长等异常场景下保持画布空白，由调用方提示
    dataUrl.value = ''
    errorMessage.value = '二维码生成失败'
  }
}

/** 获取当前二维码的 PNG DataURL（供打印 / 下载使用），未生成时返回空串 */
function getDataUrl(): string {
  return dataUrl.value
}

watch(
  () => [props.value, props.size],
  () => {
    void render()
  }
)

onMounted(() => {
  void render()
})

defineExpose({ getDataUrl, errorMessage })
</script>

<style scoped lang="scss">
.qr-code {
  display: block;
  margin: 0 auto;
  background-color: #fff;
}
</style>
