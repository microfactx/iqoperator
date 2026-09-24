"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Loader2,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Zap,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

type Signal = "call" | "put";

type Feedback = { kind: "success" | "error"; text: string } | null;

const HOLD_DURATION_MS = 400;
const FALLBACK_ASSETS = [
  "EURUSD-OTC",
  "GBPUSD-OTC",
  "USDJPY-OTC",
  "AUDUSD-OTC",
  "EURGBP-OTC",
  "USDCAD-OTC",
];
const QUICK_STAKES = ["2", "5", "10", "20", "50"];

export function TradeTicket({
  defaultStake = "2",
  onExecuted,
}: {
  defaultStake?: string;
  onExecuted?: () => void;
}) {
  const [stake, setStake] = useState<string>(defaultStake);
  const [asset, setAsset] = useState<string>(FALLBACK_ASSETS[0]);
  const [assets, setAssets] = useState<string[]>(FALLBACK_ASSETS);
  const [executing, setExecuting] = useState<Signal | null>(null);
  const [holdingSignal, setHoldingSignal] = useState<Signal | null>(null);
  const [feedback, setFeedback] = useState<Feedback>(null);

  const holdTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const feedbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const holdingSignalRef = useRef<Signal | null>(null);

  const cancelHold = useCallback((signal?: Signal) => {
    if (signal && holdingSignalRef.current !== signal) return;
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    holdingSignalRef.current = null;
    setHoldingSignal(null);
  }, []);

  useEffect(() => {
    fetch("/api/manual")
      .then((x) => x.json())
      .then((b) => {
        const list = Array.isArray(b?.assets)
          ? b.assets
              .map((a: any) => String(a.asset || a))
              .flatMap((s: string) =>
                s
                  .split(",")
                  .map((x) => x.trim())
                  .filter(Boolean)
              )
          : null;
        if (list && list.length) {
          setAssets(list);
          setAsset((cur) => (list.includes(cur) ? cur : list[0]));
        }
      })
      .catch(() => null);

    const onWindowBlur = () => cancelHold();
    window.addEventListener("blur", onWindowBlur);

    return () => {
      window.removeEventListener("blur", onWindowBlur);
      if (holdTimerRef.current) clearTimeout(holdTimerRef.current);
      if (feedbackTimerRef.current) clearTimeout(feedbackTimerRef.current);
    };
  }, [cancelHold]);

  const showFeedback = useCallback((next: NonNullable<Feedback>) => {
    setFeedback(next);
    if (feedbackTimerRef.current) clearTimeout(feedbackTimerRef.current);
    feedbackTimerRef.current = setTimeout(() => setFeedback(null), 4500);
  }, []);

  const executeTrade = useCallback(
    async (signal: Signal) => {
      const cleanStake = String(stake).replace(",", ".");
      const stakeNum = Number(cleanStake);
      const label = signal === "call" ? "CALL" : "PUT";
      setExecuting(signal);
      cancelHold();

      try {
        const res = await fetch("/api/manual", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ signal, asset, stake: stakeNum }),
        });
        const data = (await res.json().catch(() => null)) as {
          ok?: boolean;
          signal?: string;
          asset?: string;
          error?: string;
        } | null;

        if (!res.ok || !data?.ok) {
          throw new Error(data?.error ? `Falha: ${data.error}` : `Falha ao enviar ${label}`);
        }

        showFeedback({
          kind: "success",
          text: `Ordem ${label} (${data.asset || asset}) enviada com stake R$ ${stakeNum.toFixed(2)}.`,
        });
        onExecuted?.();
      } catch (err) {
        showFeedback({
          kind: "error",
          text: err instanceof Error ? err.message : "Erro ao enviar operação.",
        });
      } finally {
        setExecuting(null);
      }
    },
    [stake, asset, cancelHold, showFeedback, onExecuted]
  );

  const startHold = useCallback(
    (signal: Signal) => {
      if (executing || holdingSignalRef.current) return;

      const cleanStake = String(stake).replace(",", ".");
      const stakeNum = Number(cleanStake);
      if (!cleanStake || Number.isNaN(stakeNum) || stakeNum <= 0) {
        showFeedback({
          kind: "error",
          text: "Informe um stake válido maior que zero.",
        });
        return;
      }

      holdingSignalRef.current = signal;
      setHoldingSignal(signal);
      if (holdTimerRef.current) clearTimeout(holdTimerRef.current);

      holdTimerRef.current = setTimeout(() => {
        executeTrade(signal);
      }, HOLD_DURATION_MS);
    },
    [executing, stake, showFeedback, executeTrade]
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent<HTMLButtonElement>, sig: Signal) => {
      const touch = e.touches[0];
      if (!touch) return;
      const rect = e.currentTarget.getBoundingClientRect();
      const isInside =
        touch.clientX >= rect.left &&
        touch.clientX <= rect.right &&
        touch.clientY >= rect.top &&
        touch.clientY <= rect.bottom;
      if (!isInside) {
        cancelHold(sig);
      }
    },
    [cancelHold]
  );

  const busy = executing !== null;

  return (
    <div className="bg-surface border border-border rounded-lg p-4 relative overflow-hidden">
      {/* Header with tactical safety badge */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <Zap size={15} className="text-accent" />
          <h3 className="text-sm font-semibold text-foreground">Operação Manual</h3>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-elevated border border-border text-[10px] font-mono text-muted">
          <ShieldCheck size={12} className="text-accent" />
          <span>Hold 400ms</span>
        </div>
      </div>

      {/* Asset Selector */}
      <div>
        <label htmlFor="trade-asset" className="block text-xs text-muted mb-1">
          Ativo
        </label>
        <select
          id="trade-asset"
          value={asset}
          disabled={busy}
          onChange={(e) => setAsset(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-accent disabled:opacity-60 transition-colors font-mono"
        >
          {assets.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>

      {/* Stake Selector & Quick Chips */}
      <div className="mt-3">
        <div className="flex items-center justify-between mb-1">
          <label htmlFor="trade-stake" className="block text-xs text-muted">
            Stake (R$)
          </label>
          <span className="text-[10px] text-muted font-mono">Conta PRACTICE</span>
        </div>
        <input
          id="trade-stake"
          type="number"
          min="1"
          step="0.5"
          value={stake}
          disabled={busy}
          onChange={(e) => setStake(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-accent disabled:opacity-60 transition-colors font-mono"
        />

        {/* Quick Stake Pills */}
        <div className="mt-1.5 flex items-center gap-1.5">
          {QUICK_STAKES.map((q) => (
            <button
              key={q}
              type="button"
              disabled={busy}
              onClick={() => setStake(q)}
              className={cn(
                "flex-1 py-1 rounded text-[11px] font-mono transition-colors",
                stake === q
                  ? "bg-accent/20 text-accent font-semibold border border-accent/40"
                  : "bg-surface-elevated hover:bg-surface-overlay text-muted hover:text-foreground border border-border/60"
              )}
            >
              +{q}
            </button>
          ))}
        </div>
      </div>

      {/* Tactile Hold-to-Execute Buttons */}
      <div className="mt-4 grid grid-cols-2 gap-2.5">
        {/* CALL Button */}
        <div className="relative">
          <button
            type="button"
            disabled={busy}
            tabIndex={0}
            onMouseDown={() => startHold("call")}
            onMouseUp={() => cancelHold("call")}
            onMouseLeave={() => cancelHold("call")}
            onBlur={() => cancelHold("call")}
            onTouchStart={() => startHold("call")}
            onTouchMove={(e) => handleTouchMove(e, "call")}
            onTouchEnd={() => cancelHold("call")}
            onTouchCancel={() => cancelHold("call")}
            onContextMenu={(e) => e.preventDefault()}
            onKeyDown={(e) => {
              if ((e.key === " " || e.key === "Enter") && !e.repeat) {
                e.preventDefault();
                startHold("call");
              }
            }}
            onKeyUp={(e) => {
              if (e.key === " " || e.key === "Enter") {
                e.preventDefault();
                cancelHold("call");
              }
            }}
            aria-label="CALL - Segure 400ms para executar"
            className={cn(
              "relative w-full h-12 rounded-lg font-semibold text-xs overflow-hidden select-none touch-none",
              "border transition-all duration-150 flex flex-col items-center justify-center gap-0.5",
              holdingSignal === "call"
                ? "border-emerald-400 shadow-[0_0_15px_rgba(61,214,140,0.35)] scale-[0.98]"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:border-emerald-500/60 hover:bg-emerald-500/15",
              busy && executing !== "call" && "opacity-40 cursor-not-allowed",
              busy && executing === "call" && "border-emerald-400 bg-emerald-500/20 text-emerald-300 cursor-wait"
            )}
          >
            {/* Animated progress fill via Framer Motion */}
            <AnimatePresence>
              {holdingSignal === "call" && (
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  exit={{ scaleX: 0, transition: { duration: 0.12, ease: "easeOut" } }}
                  transition={{ duration: HOLD_DURATION_MS / 1000, ease: "linear" }}
                  className="absolute inset-0 origin-left bg-emerald-500 z-0"
                />
              )}
            </AnimatePresence>

            <span
              className={cn(
                "relative z-10 flex items-center justify-center gap-1 font-bold tracking-wide transition-colors",
                holdingSignal === "call" ? "text-black" : "text-emerald-400"
              )}
            >
              {executing === "call" ? (
                <>
                  <Loader2 size={14} className="animate-spin text-emerald-400" />
                  <span>ENVIANDO...</span>
                </>
              ) : holdingSignal === "call" ? (
                <>
                  <ArrowUpRight size={15} className="text-black animate-pulse" />
                  <span>CONFIRMANDO...</span>
                </>
              ) : (
                <>
                  <ArrowUpRight size={15} />
                  <span>CALL</span>
                </>
              )}
            </span>

            {/* Instruction subtext */}
            {executing !== "call" && (
              <span
                className={cn(
                  "relative z-10 text-[9px] font-mono transition-colors",
                  holdingSignal === "call" ? "text-black/80 font-bold" : "text-emerald-400/70"
                )}
              >
                {holdingSignal === "call" ? "SEGURE..." : "SEGURE 400MS"}
              </span>
            )}
          </button>
        </div>

        {/* PUT Button */}
        <div className="relative">
          <button
            type="button"
            disabled={busy}
            tabIndex={0}
            onMouseDown={() => startHold("put")}
            onMouseUp={() => cancelHold("put")}
            onMouseLeave={() => cancelHold("put")}
            onBlur={() => cancelHold("put")}
            onTouchStart={() => startHold("put")}
            onTouchMove={(e) => handleTouchMove(e, "put")}
            onTouchEnd={() => cancelHold("put")}
            onTouchCancel={() => cancelHold("put")}
            onContextMenu={(e) => e.preventDefault()}
            onKeyDown={(e) => {
              if ((e.key === " " || e.key === "Enter") && !e.repeat) {
                e.preventDefault();
                startHold("put");
              }
            }}
            onKeyUp={(e) => {
              if (e.key === " " || e.key === "Enter") {
                e.preventDefault();
                cancelHold("put");
              }
            }}
            aria-label="PUT - Segure 400ms para executar"
            className={cn(
              "relative w-full h-12 rounded-lg font-semibold text-xs overflow-hidden select-none touch-none",
              "border transition-all duration-150 flex flex-col items-center justify-center gap-0.5",
              holdingSignal === "put"
                ? "border-rose-400 shadow-[0_0_15px_rgba(255,84,112,0.35)] scale-[0.98]"
                : "border-rose-500/30 bg-rose-500/10 text-rose-400 hover:border-rose-500/60 hover:bg-rose-500/15",
              busy && executing !== "put" && "opacity-40 cursor-not-allowed",
              busy && executing === "put" && "border-rose-400 bg-rose-500/20 text-rose-300 cursor-wait"
            )}
          >
            {/* Animated progress fill via Framer Motion */}
            <AnimatePresence>
              {holdingSignal === "put" && (
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  exit={{ scaleX: 0, transition: { duration: 0.12, ease: "easeOut" } }}
                  transition={{ duration: HOLD_DURATION_MS / 1000, ease: "linear" }}
                  className="absolute inset-0 origin-left bg-rose-500 z-0"
                />
              )}
            </AnimatePresence>

            <span
              className={cn(
                "relative z-10 flex items-center justify-center gap-1 font-bold tracking-wide transition-colors",
                holdingSignal === "put" ? "text-white" : "text-rose-400"
              )}
            >
              {executing === "put" ? (
                <>
                  <Loader2 size={14} className="animate-spin text-rose-400" />
                  <span>ENVIANDO...</span>
                </>
              ) : holdingSignal === "put" ? (
                <>
                  <ArrowDownRight size={15} className="text-white animate-pulse" />
                  <span>CONFIRMANDO...</span>
                </>
              ) : (
                <>
                  <ArrowDownRight size={15} />
                  <span>PUT</span>
                </>
              )}
            </span>

            {/* Instruction subtext */}
            {executing !== "put" && (
              <span
                className={cn(
                  "relative z-10 text-[9px] font-mono transition-colors",
                  holdingSignal === "put" ? "text-white/90 font-bold" : "text-rose-400/70"
                )}
              >
                {holdingSignal === "put" ? "SEGURE..." : "SEGURE 400MS"}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Modern HUD Feedback Toast/Banner */}
      <AnimatePresence>
        {feedback && (
          <motion.div
            initial={{ opacity: 0, y: -6, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -6, height: 0 }}
            transition={{ duration: 0.2 }}
            role={feedback.kind === "error" ? "alert" : "status"}
            className={cn(
              "mt-3 rounded-md px-3 py-2 text-xs font-mono flex items-start gap-2 border",
              feedback.kind === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-rose-500/10 border-rose-500/30 text-rose-400"
            )}
          >
            {feedback.kind === "success" ? (
              <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-emerald-400" />
            ) : (
              <AlertCircle size={14} className="shrink-0 mt-0.5 text-rose-400" />
            )}
            <span className="flex-1 leading-snug">{feedback.text}</span>
          </motion.div>
        )}
      </AnimatePresence>

      <p className="mt-3 text-[11px] leading-relaxed text-muted font-mono flex items-center justify-between">
        <span>execução sem bloqueio de janela</span>
        <span>teto respeitado</span>
      </p>
    </div>
  );
}
