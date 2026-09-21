import * as React from "react"
import { cn } from "@/lib/utils"

// Fundo institucional: grid + spotlight + orbes sutis (Aceternity UI, MIT — port CSS puro)
// Base estática (GPU ~zero) + spotlight animado uma vez no mount
export function AppBackground({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("pointer-events-none fixed inset-0 z-0 overflow-hidden bg-[#0B0E14]", className)}
    >
      {/* grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(148,163,184,0.09)_1px,transparent_1px),linear-gradient(to_bottom,rgba(148,163,184,0.09)_1px,transparent_1px)] bg-[size:44px_44px] [mask-image:radial-gradient(ellipse_80%_60%_at_50%_0%,black_35%,transparent_100%)]" />
      {/* spotlight cyan (esquerda) */}
      <svg
        className="animate-spotlight absolute -top-40 left-0 h-[480px] w-[720px] opacity-0 md:left-40"
        viewBox="0 0 378 368"
      >
        <ellipse cx="192" cy="180" rx="192" ry="180" fill="#22D3EE" fillOpacity="0.10" />
      </svg>
      {/* spotlight indigo (direita) */}
      <svg
        className="animate-spotlight absolute -top-32 right-[-160px] h-[420px] w-[640px] opacity-0"
        viewBox="0 0 378 368"
        style={{ animationDelay: "1.1s" }}
      >
        <ellipse cx="192" cy="180" rx="192" ry="180" fill="#6366F1" fillOpacity="0.12" />
      </svg>
      {/* orbe verde trading (canto inferior) */}
      <div className="absolute -bottom-40 -left-32 h-[380px] w-[380px] rounded-full bg-[radial-gradient(circle,rgba(61,214,140,0.10)_0%,transparent_70%)] blur-[60px]" />
      {/* vinheta inferior para leitura das tabelas */}
      <div className="absolute inset-x-0 bottom-0 h-64 bg-gradient-to-t from-[#0B0E14] to-transparent" />
    </div>
  )
}