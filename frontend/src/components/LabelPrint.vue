<template>
  <div
    class="label-print"
    :class="{
      'label-print--single': printingIndex !== null,
      'label-print--paper-label': printPaper === 'label'
    }"
  >
    <div class="label-print__toolbar no-print">
      <el-button
        type="primary"
        :icon="Printer"
        :disabled="!items.length"
        @click="printAll"
      >
        打印全部{{ items.length ? `（${items.length} 张）` : '' }}
      </el-button>

      <el-button :icon="CopyDocument" :disabled="!items.length" @click="copyAll">
        复制全部
      </el-button>

      <div class="label-print__paper">
        <span class="label-print__paper-label">打印纸张</span>
        <el-radio-group v-model="printPaper" size="small">
          <el-radio-button value="label">标签纸 40×40</el-radio-button>
          <el-radio-button value="a4">A4</el-radio-button>
        </el-radio-group>
      </div>

      <span class="label-print__hint">标签尺寸 40×40mm · 点击任一标签可单独查看/打印</span>
    </div>

    <el-empty v-if="!items.length" description="暂无可打印的标签" />

    <div v-else class="label-print__area">
      <div
        v-for="(item, index) in items"
        :key="`${item.itemCode}-${index}`"
        class="label-print__cell"
        :class="{ 'is-print-target': printingIndex === index }"
        role="button"
        tabindex="0"
        @click="openPreview(index)"
        @keydown.enter.prevent="openPreview(index)"
        @keydown.space.prevent="openPreview(index)"
      >
        <LabelCard :item="item" />
        <span class="label-print__cell-tip no-print">点击查看</span>
      </div>
    </div>

    <el-dialog
      v-model="previewVisible"
      title="标签预览"
      width="min(92vw, 420px)"
      class="label-preview-dialog no-print"
      modal-class="no-print"
      append-to-body
      destroy-on-close
    >
      <div v-if="previewItem" class="label-preview">
        <div class="label-preview__stage">
          <LabelCard :item="previewItem" class="label-preview__card" />
        </div>
      </div>

      <template #footer>
        <el-button :icon="CopyDocument" @click="copyPreview">复制</el-button>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button :disabled="!previewItem?.id" @click="openStandalone">单独打开</el-button>
        <el-button type="primary" :icon="Printer" @click="printPreview">打印此标签</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { CopyDocument, Printer } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

import LabelCard from '@/components/LabelCard.vue'
import type { LabelItem } from '@/types/label'
import { copyText, toTsvRow } from '@/utils/clipboard'

/** 打印纸张：标签纸 40×40（一页一张）/ A4（一页多张） */
type PrintPaper = 'label' | 'a4'

const PAPER_KEY = 'fleetparts:label-paper'
/** 动态注入的 @page 样式节点 ID */
const PAGE_STYLE_ID = 'fleetparts-label-page-style'

const props = defineProps<{
  /** 标签数据，一条数据一张标签 */
  items: LabelItem[]
}>()

const router = useRouter()

const previewIndex = ref<number | null>(null)
const previewVisible = ref(false)
/** 正在单独打印的标签下标；null 表示打印全部 */
const printingIndex = ref<number | null>(null)
const printPaper = ref<PrintPaper>(readPaper())

const previewItem = computed<LabelItem | null>(() =>
  previewIndex.value === null ? null : (props.items[previewIndex.value] ?? null)
)

function readPaper(): PrintPaper {
  return localStorage.getItem(PAPER_KEY) === 'a4' ? 'a4' : 'label'
}

/** 写入当前纸张尺寸，保证 40×40 标签纸一页一张、A4 一页多张 */
function applyPageStyle() {
  let styleEl = document.getElementById(PAGE_STYLE_ID)
  if (!styleEl) {
    styleEl = document.createElement('style')
    styleEl.id = PAGE_STYLE_ID
    document.head.appendChild(styleEl)
  }
  styleEl.textContent =
    printPaper.value === 'a4'
      ? '@media print { @page { size: A4 portrait; margin: 6mm; } }'
      : '@media print { @page { size: 40mm 40mm; margin: 0; } }'
}

watch(printPaper, (value) => {
  localStorage.setItem(PAPER_KEY, value)
  applyPageStyle()
})

/** 打开单张预览（手机端可放大查看并单独打印） */
function openPreview(index: number) {
  previewIndex.value = index
  previewVisible.value = true
}

/**
 * 触发打印。
 * target 为 null 时打印全部标签；否则只打印该下标对应的标签。
 */
async function runPrint(target: number | null) {
  if (!props.items.length) {
    return
  }
  applyPageStyle()
  printingIndex.value = target
  await nextTick()
  window.print()
}

function printAll() {
  previewVisible.value = false
  void runPrint(null)
}

function printPreview() {
  const index = previewIndex.value
  if (index === null) {
    return
  }
  // 预览弹层带 no-print，打印时不会输出，无需关闭
  void runPrint(index)
}

/** 在新窗口单独打开该标签，便于手机端分享链接或单独查看 */
function openStandalone() {
  const item = previewItem.value
  if (!item?.id) {
    ElMessage.warning('该标签缺少库存件ID，无法单独打开')
    return
  }
  const { href } = router.resolve({
    path: '/inventory/item/print',
    query: { id: String(item.id) }
  })
  const opened = window.open(href, '_blank')
  if (!opened) {
    ElMessage.warning('浏览器阻止了新窗口，请允许本站弹出窗口后重试')
  }
}

/**
 * 把一条标签拼成制表符分隔的一行，字段顺序固定为：
 * 配件名 → 规格型号 → 库位 → 批次号 → 库存编码。
 * 粘贴到 Excel 后会按列拆分，顺序与现场核对表一致，禁止调整。
 */
function buildLabelRow(item: LabelItem): string {
  return toTsvRow([item.partName, item.spec, item.locationCode, item.batchNo, item.itemCode])
}

/** 复制当前预览标签的一行内容（配件名 / 规格型号 / 库位 / 批次号 / 库存编码） */
async function copyPreview() {
  const item = previewItem.value
  if (!item) {
    return
  }
  const copied = await copyText(buildLabelRow(item))
  if (copied) {
    ElMessage.success('已复制到剪贴板，可直接粘贴到 Excel')
  } else {
    ElMessage.error('复制失败，请允许浏览器访问剪贴板后重试')
  }
}

/** 复制全部标签内容，一条标签一行，便于批量粘贴到 Excel */
async function copyAll() {
  if (!props.items.length) {
    return
  }
  const copied = await copyText(props.items.map(buildLabelRow).join('\n'))
  if (copied) {
    ElMessage.success(`已复制 ${props.items.length} 条标签内容，可直接粘贴到 Excel`)
  } else {
    ElMessage.error('复制失败，请允许浏览器访问剪贴板后重试')
  }
}

function handleAfterPrint() {
  printingIndex.value = null
}

onMounted(() => {
  applyPageStyle()
  window.addEventListener('afterprint', handleAfterPrint)
})

onBeforeUnmount(() => {
  window.removeEventListener('afterprint', handleAfterPrint)
  document.getElementById(PAGE_STYLE_ID)?.remove()
})
</script>

<style lang="scss">
.label-print {
  .label-print__toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    margin-bottom: 12px;
  }

  .label-print__paper {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .label-print__paper-label,
  .label-print__hint {
    font-size: 13px;
    color: #909399;
  }

  .label-print__area {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding: 12px;
    background-color: #f5f7fa;
    border-radius: 4px;
  }

  .label-print__cell {
    position: relative;
    cursor: zoom-in;
    user-select: none;
    border-radius: 2px;
    -webkit-tap-highlight-color: transparent;

    &:hover,
    &:focus-visible {
      outline: 2px solid var(--el-color-primary);
      outline-offset: 1px;
    }
  }

  .label-print__cell-tip {
    position: absolute;
    right: 2px;
    bottom: 2px;
    padding: 0 6px;
    font-size: 12px;
    line-height: 18px;
    color: #fff;
    pointer-events: none;
    background-color: rgba(0, 0, 0, 0.45);
    border-radius: 2px;
    opacity: 0;
    transition: opacity 0.15s ease;
  }

  .label-print__cell:hover .label-print__cell-tip {
    opacity: 1;
  }

  /* 触屏设备没有 hover，常显"点击查看"角标 */
  @media (hover: none) {
    .label-print__cell-tip {
      opacity: 1;
    }
  }
}

.label-preview-dialog {
  --el-dialog-margin-top: 6vh;
}

.label-preview {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;

  &__stage {
    --preview-zoom: 2;

    position: relative;
    width: calc(40mm * var(--preview-zoom));
    height: calc(40mm * var(--preview-zoom));
  }

  &__card {
    transform: scale(var(--preview-zoom));
    transform-origin: top left;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.18);
  }
}

@media (max-width: 767px) {
  .label-print {
    .label-print__toolbar {
      gap: 8px;
    }

    .label-print__hint {
      font-size: 12px;
    }

    .label-print__area {
      gap: 8px;
      justify-content: center;
      padding: 8px;
    }
  }

  /* 预览只展示 40×40 标签本体，手机上适当缩放避免溢出 */
  .label-preview__stage {
    --preview-zoom: 1.8;
  }
}

@media (max-width: 380px) {
  .label-preview__stage {
    --preview-zoom: 1.6;
  }
}

@media print {
  /* 打印时工具栏、查看提示全部隐藏 */
  .label-print .label-print__toolbar,
  .label-print .label-print__cell-tip {
    display: none !important;
  }

  .label-print .label-print__area {
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    padding: 0 !important;
    background: transparent !important;
  }

  .label-print .label-print__cell {
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .label-print .label {
    border: none;
    border-radius: 0;
    box-shadow: none;
  }

  /* 标签纸 40×40：一张标签一页，避免纸张高度舍入导致串页 */
  .label-print.label-print--paper-label .label-print__cell {
    break-after: page;
    page-break-after: always;
  }

  .label-print.label-print--paper-label .label-print__cell:last-child {
    break-after: auto;
    page-break-after: auto;
  }

  /* 单张打印：只输出目标标签 */
  .label-print.label-print--single .label-print__cell {
    display: none !important;
  }

  .label-print.label-print--single .label-print__cell.is-print-target {
    display: block !important;
  }

  /* 单张 + 标签纸只有一页，避免 break-after 产生空白页 */
  .label-print.label-print--single.label-print--paper-label
    .label-print__cell.is-print-target {
    break-after: auto;
    page-break-after: auto;
  }
}
</style>
