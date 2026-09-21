import * as React from "react"
import { Table, TableBody, TableCell, TableHeader, TableHeaderRow, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"

export interface DataGridColumn {
  accessorKey: string
  header: string
  cellClassName?: string
}

export interface DataGridTableProps {
  columns: DataGridColumn[]
  data: Record<string, any>[]
  className?: string
}

export function DataGridTable({ columns, data, className }: DataGridTableProps) {
  const [sortKey, setSortKey] = React.useState<string | null>(null)
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("asc")
  const [hidden, setHidden] = React.useState<Set<string>>(new Set())

  const visibleColumns = columns.filter((c) => !hidden.has(c.accessorKey))

  const rows = React.useMemo(() => {
    if (!sortKey) return data
    const sorted = [...data].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      const an = parseFloat(av)
      const bn = parseFloat(bv)
      if (!isNaN(an) && !isNaN(bn)) return sortDir === "asc" ? an - bn : bn - an
      const cmp = String(av).localeCompare(String(bv))
      return sortDir === "asc" ? cmp : -cmp
    })
    return sorted
  }, [data, sortKey, sortDir])

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    } else {
      setSortKey(key)
      setSortDir("asc")
    }
  }

  function toggleColumn(key: string) {
    setHidden((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const sortIcon = (key: string) => {
    if (sortKey !== key) return <span className="ml-1 text-xs opacity-40">⇅</span>
    return sortDir === "asc" ? <span className="ml-1 text-xs">↑</span> : <span className="ml-1 text-xs">↓</span>
  }

  return (
    <div className="w-full">
      <div className="flex flex-wrap gap-2 mb-3">
        {columns.map((c) => (
          <button
            key={c.accessorKey}
            onClick={() => toggleColumn(c.accessorKey)}
            className={cn(
              "text-xs px-2 py-1 rounded border transition-colors",
              hidden.has(c.accessorKey)
                ? "border-border text-muted opacity-50 line-through"
                : "border-border bg-surface text-foreground hover:bg-muted/20"
            )}
          >
            {c.header}
          </button>
        ))}
      </div>
      <Table className={cn("rounded-lg border border-border", className)}>
        <TableHeader>
          <TableHeaderRow>
            {visibleColumns.map((c) => (
              <TableCell
                key={c.accessorKey}
                className="font-semibold text-xs uppercase tracking-wide text-muted cursor-pointer select-none hover:text-foreground"
                onClick={() => toggleSort(c.accessorKey)}
              >
                <span className="inline-flex items-center">
                  {c.header}
                  {sortIcon(c.accessorKey)}
                </span>
              </TableCell>
            ))}
          </TableHeaderRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={visibleColumns.length} className="text-center py-8 text-muted">
                Nenhum dado disponível
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row, i) => (
              <TableRow
                key={i}
                className={cn("transition-colors", i % 2 === 1 ? "bg-background/40" : "")}
              >
                {visibleColumns.map((c) => (
                  <TableCell key={c.accessorKey} className={cn("font-mono text-xs", c.cellClassName)}>
                    {renderValue(row[c.accessorKey], c.accessorKey)}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}

function renderValue(value: any, key: string): React.ReactNode {
  const v = value === undefined || value === null ? "—" : String(value)
  if (key === "profit") {
    const n = parseFloat(v)
    if (isNaN(n)) return v
    return (
      <span className={n >= 0 ? "text-success" : "text-destructive"}>
        {n >= 0 ? "+" : ""}
        {n.toFixed(2)}
      </span>
    )
  }
  if (key === "signal") {
    const s = v.toLowerCase()
    return (
      <span className={s.includes("call") ? "text-success font-bold" : s.includes("put") ? "text-destructive font-bold" : "text-muted"}>
        {v}
      </span>
    )
  }
  return v
}