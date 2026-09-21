/**
 * Utility function to merge class names (shadcn/ui pattern)
 * Similar to clsx but simpler for Tailwind CSS
 */
export function cn(...classes: (string | undefined | boolean | null)[]) {
  return classes.filter(Boolean).join(" ")
}

export function formatCurrency(value: number | string, currency: "BRL" | "USD" = "BRL"): string {
  const num = typeof value === "number" ? value : parseFloat(value as string)
  if (isNaN(num)) return "R$ 0,00"
  
  if (currency === "BRL") {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num)
  }
  
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num)
}

export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

export function formatTimeAgo(date: Date | string): string {
  const now = new Date()
  const dateObj = typeof date === "string" ? new Date(date) : date
  const diffMs = now.getTime() - dateObj.getTime()
  const diffMinutes = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMinutes < 1) return "agora mesmo"
  if (diffMinutes < 60) return `${diffMinutes} min atrás`
  if (diffHours < 24) return `${diffHours} h atrás`
  if (diffDays < 30) return `${diffDays} d atrás`
  return `${Math.floor(diffDays / 30)} m atrás`
}