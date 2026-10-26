/**
 * ECharts 按需引入。
 *
 * 只注册看板 / 报表实际用到的图表与组件，避免全量引入导致打包体积过大。
 * 新增图表类型时在此补充 use([...]) 即可。
 */
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  CanvasRenderer
])

export { echarts }
export type { EChartsType } from 'echarts/core'
