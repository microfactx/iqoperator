import { cn } from "@/lib/utils"
import * as React from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderRow,
  TableRow,
} from "components/ui/table"
import { 
  Loader2, 
  ChevronUpDown, 
  AlertCircle, 
  TrendingUp, 
  TrendingDown,
  MapPin,
  Users,
  DollarSign,
  Clipboard,
  Settings,
  LogOut,
} from "lucide-react"
import { useSortedTable } from "@/hooks/use-sorted-table"
import { useTable } from "@tanstack/react-table"
import { useEffect, useState } from "react"
import { fr } from "date-fns/locale"

// ReUI Data Grid Table - Trading Cockpit
// Based on: https://21st.dev/@sean0205/components/data-grid-table

export interface DataGridColumn {
  accessorKey: string
  header: string
  className?: string
}

export interface DataGridTableProps {
  columns: DataGridColumn[]
  data: any[]
  className?: string
  width?: "full" | "fixed"
}

export function DataGridTable({ columns, data, className, width = "full": DataGridTableProps }) {
  const [sorting, setSorting] = useState<{ key: string; direction: "asc" | "desc" }[]>([])
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>(new Array(columns.length).fill(true))
  const [selectedRowIds, setSelectedRowIds] = useState<Set<string>>(new Set())

  const {
    getTableProps,
    getTableBodyProps,
    getNoContentProps,
    headerGroups,
    prepareRow,
    state: { flattenedColumns, pageOptions },
  } = useTable({
    columns: columns.map((col, i) => ({
      accessorKey: col.accessorKey,
      header: col.header,
      cell: info => <span>{React.formatString(info.getValue())}</span>,
    })),
    initialState: { sorting },
    state: { columnVisibility, selectedRowIds },
  })

  useEffect(() => {
    // Sync column visibility with state
    setColumnVisibility(prev => {
      const next = [...prev]
      return next
    })
  }, [sortedColumns])

  return (
    <Table {...getTableProps()} className={cn("w-full rounded-border", className)} {...getTableBodyProps()}>
      <TableHeader {...getTableProps()}>
        {headerGroups.map(headerGroup => (
          <TableHeaderRow key={headerGroup.id} {...headerGroup.getHeaderGroupProps()}>
            {headerGroup.headers.map(header => (
              <TableCell
                key={header.id}
                {...header.getHeaderProps(columnVisibility[header.index])}
              >
                {typeof header.isSorted === "boolean"
                  ? <ChevronUpDown className="h-4 w-4 opacity-50"/>
                  : null}
                {header.column.columnDef.header}
                <button
                  className="absolute right-2 text-xs opacity-0 hover:opacity-100 transition-opacity"
                  onClick={() => setColumnVisibility(prev => {
                    const newVis = [...prev]
                    newVis[header.index] = !newVis[header.index]
                    return newVis
                  })}
                >
                  Visibilidade
                </button>
              </TableCell>
            ))}
          </TableHeaderRow>
        ))}
      </TableHeader>

      <TableBody {...getTableBodyProps()}>
        {state.data.length === 0 && (
          <TableRow {...getNoContentProps()}>
            <TableCell colSpan={columns.length} className="text-center py-8 text-muted-foreground">
              <Loader2 className="h-6 w-6 mx-auto -mt-1 opacity-50" />
              <p className="mt-2">Nenhum dado disponível</p>
          </TableRow>
        )}

        {state.data.map(row => {
          prepareRow(row)
          return (
            <TableRow
              key={row.id}
              {...row.getRowProps()}
              className={cn(
                "hover:bg-muted/50",
                row.getRowProps().className
              )}
            >
              {flattenedColumns.map(column => {
                return (
                  <TableCell
                    key={column.id}
                    {...column.getCellProps()}
                    className={cn(
                      "p-3 text-sm",
                      column.columnDef.cellClassName
                    )}
                  >
                    {column.columnDef.enableSorting !== false && column.canSort ? (
                      <span
                        onClick={() => setSorting(prev => {
                          const newSorting = prev.map(s =>
                            s.key === column.accessorKey
                              ? { key: column.accessorKey, direction: s.direction === "asc" ? "desc" : "asc" }
                              : { key: column.accessorKey, direction: "asc" }
                          )
                          setSorting(newSorting)
                        })}
                        cursor-pointer
                        className={cn(
                          "relative after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-0 after:h-0 after:transition-colors after:duration-200 after:bg-primary/20 data-[state=selected]:after:bg-primary/50",
                          sorting.find(s => s.key === column.accessorKey)?.direction === "asc" ? "after:w-1/2 after:left-0 after:bg-primary" : sorting.find(s => s.key === column.accessorKey)?.direction === "desc" ? "after:w-1/2 after:right-0 after:bg-primary" : "after:w-0"
                        )}
                      >
                        {column.columnDef.cell ? (
                          <column.columnDef.cell />
                        ) : (
                          React.formatString(column.accessorKey)
                        )}
                        {sorting.find(s => s.key === column.accessorKey)?.direction === "asc" ? (
                          <ChevronUpDown className="h-3 w-3 ml-1 opacity-60"/>
                        ) : sorting.find(s => s.key === column.accessorKey)?.direction === "desc" ? (
                          <ChevronDown className="h-3 w-3 ml-1 opacity-60"/>
                        ) : null}
                      </span>
                    ) : (
                      <span>{React.formatString(column.accessorKey)}</span>
                    )}
                  </TableCell>
                )
              })}
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}

/* 
 * Hooks auxiliares para a tabela
 */

export function useSortedTable() {
  const [sortedColumn, setSortedColumn] = useState<string | null>(null)
  const [sortedDirection, setSortedDirection] = useState<"asc" | "desc">("asc")

  const sortedColumns = useMemo(() => {
    if (!sortedColumn) return []
    return [
      {
        accessorKey: sortedColumn,
        direction: sortedDirection,
      },
    ]
  }, [sortedColumn, sortedDirection])

  return { sortedColumn, setSortedColumn, sortedDirection, setSortedDirection, sortedColumns }
}