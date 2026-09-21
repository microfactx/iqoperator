import * as React from "react"
import { cn } from "@/lib/utils"

// Marca IQOperator — hexágono + pulso de trading (SVG puro, zero-dep)
// Inspirado em: Aceternity/shadcn icons (MIT) + direção própria hex-pulso
export function LogoMark({ size = 36, className }: { size?: number; className?: string }) {
  const gid = React.useId()
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      className={cn("shrink-0", className)}
      role="img"
      aria-label="IQOperator"
    >
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#3DD68C" />
          <stop offset="1" stopColor="#0066FF" />
        </linearGradient>
      </defs>
      <polygon
        points="32,5 59,18 59,46 32,59 5,46 5,18"
        stroke="#232A36"
        strokeWidth="2.5"
      />
      <path
        d="M12,36 L24,36 L29,26 L35,44 L40,32 L52,32"
        stroke={`url(#${gid})`}
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="52" cy="32" r="3.5" fill="#3DD68C" />
    </svg>
  )
}

// Wordmark: "IQ" branco + "Operator" em gradiente animado (Magic UI animated-gradient-text, MIT)
export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex flex-col leading-none">
      <span className={cn("font-extrabold tracking-tight text-foreground", compact ? "text-lg" : "text-2xl")}>
        IQ<span className="text-gradient-animated">Operator</span>
      </span>
      {!compact && (
        <span className="text-[11px] font-medium tracking-[0.22em] text-muted uppercase mt-1">
          microfactx · trading bot
        </span>
      )}
    </div>
  )
}

export function Brand({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <LogoMark size={compact ? 30 : 40} />
      <Wordmark compact={compact} />
    </div>
  )
}