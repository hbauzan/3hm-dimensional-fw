import { useEffect, useRef } from 'react'
import { BarChart, LineChart, ScatterChart } from 'echarts/charts'
import { DataZoomComponent, GridComponent, TooltipComponent } from 'echarts/components'
import { init, use as registerEcharts, type EChartsCoreOption, type EChartsType } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

registerEcharts([
  LineChart,
  BarChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  CanvasRenderer,
])

export function Fhv1EChartsCanvas({
  option,
  label,
}: {
  option: EChartsCoreOption
  label: string
}) {
  const node = useRef<HTMLDivElement>(null)
  const chart = useRef<EChartsType | null>(null)

  useEffect(() => {
    const host = node.current
    if (!host) return
    const instance = init(host, undefined, { renderer: 'canvas' })
    chart.current = instance
    const observer =
      typeof ResizeObserver === 'undefined'
        ? null
        : new ResizeObserver(() => {
            instance.resize()
          })
    observer?.observe(host)
    return () => {
      observer?.disconnect()
      instance.dispose()
      chart.current = null
    }
  }, [])

  useEffect(() => {
    chart.current?.setOption(option, true)
  }, [option])

  return <div ref={node} role="img" aria-label={label} className="h-64 w-full shrink-0" />
}
