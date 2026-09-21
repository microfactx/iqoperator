import * as React from "react"
import { cn } from "@/lib/utils"

export interface TableProps {
  className?: string
  children: React.ReactNode
}

export function Table({ className, children }: TableProps) {
  return (
    <table
      className={cn(
        "w-full rounded-border border-border",
        "mt-4",
        "overflow-hidden",
        className,
      )}
    >
      {children}
    </table>
  )
}

export interface TableHeaderProps {
  className?: string
  children: React.ReactNode
}

export function TableHeader({ className, children }: TableHeaderProps) {
  return (
    <thead>
      {children}
    </thead>
  )
}

export interface TableRowProps {
  className?: string
  children: React.ReactNode
  onClick?: () => void
}

export function TableRow({ className, children, onClick, ...rest }: TableRowProps) {
  const commonClassName = cn(
    "border-y",
    "last:border-0",
    "hover:bg-muted/50",
    className,
  )

  return (
    <tr
      className={commonClassName}
      onClick={onClick}
      {...rest}
    >
      {children}
    </tr>
  )
}

export interface TableCellProps {
  className?: string
  children: React.ReactNode
  colSpan?: number
}

export function TableCell({ className, children, colSpan, ...rest }: TableCellProps) {
  const commonClassName = cn(
    "p-3",
    "text-sm",
    "font-medium",
    "transition-colors",
    "hover:bg-muted/50",
    colSpan && `col-span-${colSpan}`,
    className,
  )

  return (
    <td
      className={commonClassName}
      colSpan={colSpan}
      {...rest}
    >
      {children}
    </td>
  )
}

export interface TableBodyProps {
  className?: string
  children: React.ReactNode
}

export function TableBody({ className, children }: TableBodyProps) {
  return (
    <tbody>{children}</tbody>
  )
}

export interface TableRowHeaderProps {
  className?: string
  children: React.ReactNode
}

export function TableRowHeader({ className, children }: TableRowHeaderProps) {
  return (
    <tr>
      {children}
    </tr>
  )
}