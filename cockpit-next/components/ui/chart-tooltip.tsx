"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export interface ChartTooltipPayloadItem {
  name?: string
  value?: any
  unit?: string
  color?: string
  fill?: string
  stroke?: string
  dataKey?: string | number
  payload?: any
  hide?: boolean
}

export interface ChartTooltipContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string
  children: React.ReactNode
}

/**
 * Tactical HUD container with backdrop-blur, dark translucent surface, and subtle border.
 */
export function ChartTooltipContainer({
  className,
  children,
  ...props
}: ChartTooltipContainerProps) {
  return (
    <div
      className={cn(
        "pointer-events-none z-50 rounded-lg p-2.5 min-w-[140px] shadow-xl",
        "backdrop-blur-md bg-surface-overlay/95 border border-white/10",
        "text-xs font-mono text-foreground select-none",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export interface ChartTooltipProps {
  active?: boolean
  payload?: ChartTooltipPayloadItem[]
  label?: string | number
  className?: string
  labelFormatter?: (label: any, payload: ChartTooltipPayloadItem[]) => React.ReactNode
  valueFormatter?: (value: any, name: string, item: ChartTooltipPayloadItem) => React.ReactNode
  hideIndicator?: boolean
  hideLabel?: boolean
  title?: React.ReactNode
  extra?: (payload: ChartTooltipPayloadItem[]) => React.ReactNode
}

/**
 * Reusable HUD Chart Tooltip for Recharts components across Cockpit.
 */
export function ChartTooltip({
  active,
  payload,
  label,
  className,
  labelFormatter,
  valueFormatter,
  hideIndicator = false,
  hideLabel = false,
  title,
  extra,
}: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  const renderedLabel = React.useMemo(() => {
    if (hideLabel) return null
    if (title) return title
    if (labelFormatter) return labelFormatter(label, payload)
    if (label !== undefined && label !== null && label !== "") {
      return typeof label === "number" ? `Trade #${label}` : String(label)
    }
    return null
  }, [hideLabel, title, labelFormatter, label, payload])

  const visibleItems = payload.filter((item) => !item.hide && item.value !== undefined)

  if (visibleItems.length === 0 && !title && !extra) {
    return null
  }

  return (
    <ChartTooltipContainer className={className}>
      {renderedLabel && (
        <div className="flex items-center justify-between gap-3 pb-1.5 mb-1.5 border-b border-white/10 text-[11px] font-semibold text-foreground/90">
          <span>{renderedLabel}</span>
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        {visibleItems.map((item, index) => {
          const itemColor =
            item.color || item.stroke || (item.fill && item.fill !== "none" ? item.fill : "#00D1A0")
          const name = item.name || String(item.dataKey || "Valor")
          const val =
            valueFormatter !== undefined
              ? valueFormatter(item.value, name, item)
              : typeof item.value === "number"
              ? item.value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })
              : String(item.value ?? "")

          return (
            <div key={`${item.dataKey || index}-${index}`} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-1.5 text-muted truncate max-w-[120px]">
                {!hideIndicator && (
                  <span
                    className="w-2 h-2 rounded-full shrink-0 shadow-[0_0_6px_currentColor]"
                    style={{ backgroundColor: itemColor, color: itemColor }}
                  />
                )}
                <span className="truncate">{name}</span>
              </div>
              <span className="font-semibold text-foreground tabular-nums shrink-0">
                {val}
                {item.unit ? ` ${item.unit}` : ""}
              </span>
            </div>
          )
        })}
      </div>

      {extra && <div className="mt-2 pt-1.5 border-t border-white/10">{extra(payload)}</div>}
    </ChartTooltipContainer>
  )
}
