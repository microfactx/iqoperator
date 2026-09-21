"use client"

import * as React from "react"
import { motion, useReducedMotion } from "framer-motion"
import { cn } from "@/lib/utils"

type BackgroundBeamsProps = {
  className?: string
}

type BackgroundGlowProps = {
  className?: string
}

// 10 beams suaves atravessando a tela (viewBox 1440x640).
// Curvas inspiradas no Aceternity Background Beams (MIT), adaptadas para o dark de trading.
const BEAM_PATHS: Array<{ d: string; gradient: string; opacity: number; width: number }> = [
  { d: "M -40 60 C 280 60 380 260 720 260 S 1120 420 1480 340", gradient: "url(#beam-cyan)", opacity: 0.32, width: 1.2 },
  { d: "M -40 130 C 300 130 420 320 760 320 S 1140 480 1480 410", gradient: "url(#beam-indigo)", opacity: 0.28, width: 1 },
  { d: "M -40 200 C 320 200 460 380 800 380 S 1160 540 1480 480", gradient: "url(#beam-green)", opacity: 0.22, width: 1 },
  { d: "M -40 270 C 340 270 500 440 840 440 S 1180 590 1480 550", gradient: "url(#beam-cyan)", opacity: 0.18, width: 1 },
  { d: "M -40 340 C 360 340 540 500 880 500 S 1200 640 1480 620", gradient: "url(#beam-indigo)", opacity: 0.24, width: 1.2 },
  { d: "M -40 20 C 240 20 360 200 680 200 S 1080 360 1480 280", gradient: "url(#beam-green)", opacity: 0.16, width: 1 },
  { d: "M -40 410 C 380 410 580 560 920 560 S 1220 690 1480 690", gradient: "url(#beam-cyan)", opacity: 0.14, width: 1 },
  { d: "M -40 480 C 400 480 620 620 960 620 S 1240 740 1480 760", gradient: "url(#beam-indigo)", opacity: 0.16, width: 1 },
  { d: "M -40 550 C 420 550 660 680 1000 680 S 1260 800 1480 830", gradient: "url(#beam-green)", opacity: 0.12, width: 1 },
  { d: "M -40 620 C 440 620 700 740 1040 740 S 1280 860 1480 900", gradient: "url(#beam-cyan)", opacity: 0.1, width: 1 },
]

// 3 partículas animadas ao longo de 3 paths (durações 8–14s, loop infinito).
const ANIMATED_BEAMS: Array<{
  path: string
  color: string
  glow: string
  duration: number
  delay: number
  size: number
}> = [
  {
    path: BEAM_PATHS[1].d,
    color: "#22D3EE",
    glow: "0 0 12px 2px rgba(34,211,238,0.8), 0 0 32px 6px rgba(34,211,238,0.25)",
    duration: 8,
    delay: 0,
    size: 7,
  },
  {
    path: BEAM_PATHS[4].d,
    color: "#6366F1",
    glow: "0 0 12px 2px rgba(99,102,241,0.8), 0 0 32px 6px rgba(99,102,241,0.25)",
    duration: 11,
    delay: 2.5,
    size: 8,
  },
  {
    path: BEAM_PATHS[2].d,
    color: "#3DD68C",
    glow: "0 0 12px 2px rgba(61,214,140,0.8), 0 0 32px 6px rgba(61,214,140,0.25)",
    duration: 14,
    delay: 5,
    size: 6,
  },
]

/**
 * Fundo animado com beams (estilo Aceternity, cores de trading dark).
 * Uso: hero / telas de marketing e login. Não usar no dashboard (pesado) — prefira `BackgroundGlow`.
 */
export function BackgroundBeams({ className }: BackgroundBeamsProps) {
  const reduceMotion = useReducedMotion()

  return (
    <div
      aria-hidden="true"
      className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}
    >
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 1440 640"
        preserveAspectRatio="xMidYMid slice"
        fill="none"
      >
        <defs>
          <linearGradient id="beam-cyan" x1="0" y1="0" x2="1440" y2="0" gradientUnits="userSpaceOnUse">
            <stop stopColor="#22D3EE" stopOpacity="0" />
            <stop offset="0.35" stopColor="#22D3EE" stopOpacity="0.6" />
            <stop offset="0.65" stopColor="#22D3EE" stopOpacity="0.6" />
            <stop offset="1" stopColor="#22D3EE" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="beam-indigo" x1="0" y1="0" x2="1440" y2="0" gradientUnits="userSpaceOnUse">
            <stop stopColor="#6366F1" stopOpacity="0" />
            <stop offset="0.35" stopColor="#6366F1" stopOpacity="0.6" />
            <stop offset="0.65" stopColor="#6366F1" stopOpacity="0.6" />
            <stop offset="1" stopColor="#6366F1" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="beam-green" x1="0" y1="0" x2="1440" y2="0" gradientUnits="userSpaceOnUse">
            <stop stopColor="#3DD68C" stopOpacity="0" />
            <stop offset="0.35" stopColor="#3DD68C" stopOpacity="0.55" />
            <stop offset="0.65" stopColor="#3DD68C" stopOpacity="0.55" />
            <stop offset="1" stopColor="#3DD68C" stopOpacity="0" />
          </linearGradient>
        </defs>

        {BEAM_PATHS.map((beam, i) => (
          <path
            key={i}
            d={beam.d}
            stroke={beam.gradient}
            strokeWidth={beam.width}
            strokeOpacity={beam.opacity}
            strokeLinecap="round"
          />
        ))}
      </svg>

      {reduceMotion ? (
        <>
          {ANIMATED_BEAMS.map((beam, i) => (
            <span
              key={i}
              className="absolute rounded-full"
              style={{
                width: beam.size,
                height: beam.size,
                left: `${22 + i * 24}%`,
                top: `${34 + i * 12}%`,
                backgroundColor: beam.color,
                opacity: 0.7,
                boxShadow: beam.glow,
              }}
            />
          ))}
        </>
      ) : (
        <>
          {ANIMATED_BEAMS.map((beam, i) => (
            <motion.div
              key={i}
              className="absolute left-0 top-0 rounded-full"
              initial={{ offsetDistance: "0%", opacity: 0 }}
              animate={{ offsetDistance: "100%", opacity: [0, 1, 1, 0] }}
              transition={{
                duration: beam.duration,
                repeat: Infinity,
                ease: "linear",
                delay: beam.delay,
                repeatDelay: 1,
              }}
              style={
                {
                  width: beam.size,
                  height: beam.size,
                  backgroundColor: beam.color,
                  boxShadow: beam.glow,
                  offsetPath: `path("${beam.path}")`,
                  offsetRotate: "0deg",
                } as React.CSSProperties
              }
            />
          ))}
        </>
      )}
    </div>
  )
}

/**
 * Versão estática leve (sem framer-motion): 3 orbes com blur.
 * Uso: dashboard e áreas logadas, onde `BackgroundBeams` seria pesado.
 */
export function BackgroundGlow({ className }: BackgroundGlowProps) {
  return (
    <div
      aria-hidden="true"
      className={cn("pointer-events-none absolute inset-0 overflow-hidden", className)}
    >
      <div
        className="absolute -top-24 left-1/4 h-72 w-72 rounded-full blur-[100px]"
        style={{ backgroundColor: "rgba(34,211,238,0.10)" }}
      />
      <div
        className="absolute -right-20 top-1/3 h-80 w-80 rounded-full blur-[110px]"
        style={{ backgroundColor: "rgba(99,102,241,0.12)" }}
      />
      <div
        className="absolute -bottom-24 left-1/3 h-72 w-72 rounded-full blur-[100px]"
        style={{ backgroundColor: "rgba(61,214,140,0.10)" }}
      />
    </div>
  )
}
