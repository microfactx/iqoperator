import * as React from "react"
import { cn } from "@/lib/utils"

// Sistema de ícones zero-dep — paths Lucide (ISC, via 21st.dev/community/icons/lucide)
// Padrão: stroke=currentColor, 24x24. Uso: <TrendingUp size={16} className="text-success" />
function I({
  children,
  size = 16,
  className,
  strokeWidth = 2,
}: {
  children: React.ReactNode
  size?: number
  className?: string
  strokeWidth?: number
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("shrink-0", className)}
      aria-hidden
    >
      {children}
    </svg>
  )
}

type P = { size?: number; className?: string }

export function IconTrophy(p: P) {
  return (
    <I {...p}>
      <path d="M8 21h8M12 17v4M7 4h10v6a5 5 0 0 1-10 0V4Z" />
      <path d="M7 6H4a1 1 0 0 0-1 1c0 2 1.5 4 4 4M17 6h3a1 1 0 0 1 1 1c0 2-1.5 4-4 4" />
    </I>
  )
}

export function IconPercent(p: P) {
  return (
    <I {...p}>
      <line x1="19" y1="5" x2="5" y2="19" />
      <circle cx="6.5" cy="6.5" r="2.5" />
      <circle cx="17.5" cy="17.5" r="2.5" />
    </I>
  )
}

export function IconTrendingUp(p: P) {
  return (
    <I {...p}>
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </I>
  )
}

export function IconTrendingDown(p: P) {
  return (
    <I {...p}>
      <polyline points="22 17 13.5 8.5 8.5 13.5 2 7" />
      <polyline points="16 17 22 17 22 11" />
    </I>
  )
}

export function IconTrades(p: P) {
  return (
    <I {...p}>
      <path d="M8 3 4 7l4 4" />
      <path d="M4 7h16" />
      <path d="m16 21 4-4-4-4" />
      <path d="M20 17H4" />
    </I>
  )
}

export function IconWallet(p: P) {
  return (
    <I {...p}>
      <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" />
      <path d="M3 5v14a2 2 0 0 0 2 2h16V7" />
      <path d="M18 12a1 1 0 0 0 0 2h4v-2h-4Z" />
    </I>
  )
}

export function IconCall(p: P) {
  return (
    <I {...p}>
      <path d="M7 17 17 7" />
      <path d="M7 7h10v10" />
    </I>
  )
}

export function IconPut(p: P) {
  return (
    <I {...p}>
      <path d="m7 7 10 10" />
      <path d="M17 7v10H7" />
    </I>
  )
}

export function IconDollar(p: P) {
  return (
    <I {...p}>
      <circle cx="12" cy="12" r="10" />
      <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8" />
      <path d="M12 6v12" />
    </I>
  )
}

export function IconBanknote(p: P) {
  return (
    <I {...p}>
      <rect x="2" y="6" width="20" height="12" rx="2" />
      <circle cx="12" cy="12" r="2" />
      <path d="M6 12h.01M18 12h.01" />
    </I>
  )
}

export function IconCalculator(p: P) {
  return (
    <I {...p}>
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <line x1="8" y1="6" x2="16" y2="6" />
      <path d="M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M8 18h.01M12 18h.01" />
      <line x1="16" y1="14" x2="16" y2="18" />
    </I>
  )
}

export function IconShieldAlert(p: P) {
  return (
    <I {...p}>
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1 1 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
      <path d="M12 8v4M12 12h.01" />
    </I>
  )
}

export function IconBot(p: P) {
  return (
    <I {...p}>
      <rect x="4" y="8" width="16" height="12" rx="2" />
      <path d="M12 8V4M8 4h8" />
      <circle cx="9" cy="14" r="1" fill="currentColor" />
      <circle cx="15" cy="14" r="1" fill="currentColor" />
      <path d="M9 18h6" />
    </I>
  )
}

export function IconPower(p: P) {
  return (
    <I {...p}>
      <path d="M12 2v10" />
      <path d="M18.4 6.6a9 9 0 1 1-12.77.04" />
    </I>
  )
}

export function IconClock(p: P) {
  return (
    <I {...p}>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </I>
  )
}

export function IconWorkflow(p: P) {
  return (
    <I {...p}>
      <rect x="3" y="3" width="6" height="6" rx="1" />
      <rect x="15" y="15" width="6" height="6" rx="1" />
      <path d="M9 6h6a3 3 0 0 1 3 3v6" />
    </I>
  )
}

export function IconCandles(p: P) {
  return (
    <I {...p}>
      <path d="M9 3v4M15 17v4M7 7h4v5H7zM13 12h4v5h-4z" />
      <path d="M5 14h8M11 9h8" />
    </I>
  )
}

export function IconBell(p: P) {
  return (
    <I {...p}>
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </I>
  )
}

export function IconFileText(p: P) {
  return (
    <I {...p}>
      <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
      <path d="M14 2v4a2 2 0 0 0 2 2h4" />
      <path d="M10 9H8M16 13H8M16 17H8" />
    </I>
  )
}

export function IconSearch(p: P) {
  return (
    <I {...p}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </I>
  )
}

export function IconDownload(p: P) {
  return (
    <I {...p}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </I>
  )
}

export function IconCopy(p: P) {
  return (
    <I {...p}>
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </I>
  )
}

export function IconCheck(p: P) {
  return (
    <I {...p}>
      <polyline points="20 6 9 17 4 12" />
    </I>
  )
}

export function IconActivity(p: P) {
  return (
    <I {...p}>
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </I>
  )
}

export function IconZap(p: P) {
  return (
    <I {...p}>
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </I>
  )
}
