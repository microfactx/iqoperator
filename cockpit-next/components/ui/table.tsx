import * as React from "react"
import { cn } from "@/lib/utils"

export interface TableProps {
  className?: string
  children: React.ReactNode
  [key: string]: any
}

export function Table({ className, children, ...props }: TableProps) {
  return (
    <table className={cn("w-full overflow-hidden", className)} {...props}>
      {children}
    </table>
  )
}

export interface TableHeaderProps {
  className?: string
  children: React.ReactNode
  [key: string]: any
}

export function TableHeader({ className, children, ...props }: TableHeaderProps) {
  return <thead className={className} {...props}>{children}</thead>
}

export interface TableHeaderRowProps {
  className?: string
  children: React.ReactNode
  [key: string]: any
}

export function TableHeaderRow({ className, children, ...props }: TableHeaderRowProps) {
  return <tr className={cn("border-b border-border", className)} {...props}>{children}</tr>
}

export interface TableRowProps {
  className?: string
  children: React.ReactNode
  [key: string]: any
}

export function TableRow({ className, children, ...props }: TableRowProps) {
  return (
    <tr
      className={cn("border-b border-border last:border-0 hover:bg-muted/50", className)}
      {...props}
    >
      {children}
    </tr>
  )
}

export interface TableBodyProps {
  className?: string
  children: React.ReactNode
  [key: string]: any
}

export function TableBody({ className, children, ...props }: TableBodyProps) {
  return <tbody className={className} {...props}>{children}</tbody>
}

export interface TableCellProps {
  className?: string
  children: React.ReactNode
  colSpan?: number
  [key: string]: any
}

export function TableCell({ className, children, colSpan, ...props }: TableCellProps) {
  return (
    <td
      className={cn("p-3 text-sm font-medium", className)}
      colSpan={colSpan}
      {...props}
    >
      {children}
    </td>
  )
}