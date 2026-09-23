"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDownRight, ArrowUpRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Signal = "call" | "put";

type Feedback = { kind: "success" | "error"; text: string } | null;

const FALLBACK_ASSETS = ["EURUSD-OTC", "GBPUSD-OTC", "USDJPY-OTC", "AUDUSD-OTC", "EURGBP-OTC", "USDCAD-OTC"];

export function TradeTicket({ defaultStake = "2" }: { defaultStake?: string }) {
  const [stake, setStake] = useState<string>(defaultStake);
  const [asset, setAsset] = useState<string>(FALLBACK_ASSETS[0]);
  const [assets, setAssets] = useState<string[]>(FALLBACK_ASSETS);
  const [loading, setLoading] = useState<Signal | null>(null);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetch("/api/manual")
      .then((x) => x.json())
      .then((b) => {
        const list = Array.isArray(b?.assets)
          ? b.assets.map((a: any) => String(a.asset || a)).flatMap((s: string) => s.split(",").map((x) => x.trim()).filter(Boolean))
          : null;
        if (list && list.length) {
          setAssets(list);
          setAsset((cur) => (list.includes(cur) ? cur : list[0]));
        }
      })
      .catch(() => null);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  function showFeedback(next: NonNullable<Feedback>) {
    setFeedback(next);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setFeedback(null), 4000);
  }

  async function handleTrade(signal: Signal) {
    const stakeNum = Number(stake);
    if (!stake || Number.isNaN(stakeNum) || stakeNum <= 0) {
      showFeedback({ kind: "error", text: "Informe um stake válido maior que zero." });
      return;
    }

    const label = signal === "call" ? "CALL" : "PUT";
    const ok = confirm(`Confirmar ${label} ${asset} com stake ${stakeNum}?`);
    if (!ok) return;

    setLoading(signal);
    try {
      const res = await fetch("/api/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ signal, asset, stake: stakeNum }),
      });
      const data = (await res.json().catch(() => null)) as { ok?: boolean; signal?: string; asset?: string; error?: string } | null;
      if (!res.ok || !data?.ok) {
        throw new Error(data?.error ? `Falha: ${data.error}` : `Falha ao enviar ${label}`);
      }
      showFeedback({ kind: "success", text: `${label} ${data.asset} enviado com stake ${stakeNum}.` });
    } catch (err) {
      showFeedback({
        kind: "error",
        text: err instanceof Error ? err.message : "Erro ao enviar operação.",
      });
    } finally {
      setLoading(null);
    }
  }

  const busy = loading !== null;

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <h3 className="text-sm font-medium">Operação Manual</h3>

      <label htmlFor="trade-asset" className="mt-3 block text-xs text-muted">
        Ativo
      </label>
      <select
        id="trade-asset"
        value={asset}
        disabled={busy}
        onChange={(e) => setAsset(e.target.value)}
        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-accent disabled:opacity-60"
      >
        {assets.map((a) => (
          <option key={a} value={a}>{a}</option>
        ))}
      </select>

      <label htmlFor="trade-stake" className="mt-3 block text-xs text-muted">
        Stake atual
      </label>
      <input
        id="trade-stake"
        type="number"
        min="0"
        step="0.5"
        value={stake}
        disabled={busy}
        onChange={(e) => setStake(e.target.value)}
        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-accent disabled:opacity-60"
      />

      <div className="mt-3 grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => handleTrade("call")}
          className={cn(
            "rounded-md bg-success px-3 py-3 text-sm font-semibold text-black",
            "inline-flex items-center justify-center gap-1.5",
            "transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          )}
        >
          {loading === "call" ? (
            <><Loader2 size={15} className="animate-spin" /> Enviando…</>
          ) : (
            <><ArrowUpRight size={15} /> CALL</>
          )}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => handleTrade("put")}
          className={cn(
            "rounded-md bg-destructive px-3 py-3 text-sm font-semibold text-white",
            "inline-flex items-center justify-center gap-1.5",
            "transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          )}
        >
          {loading === "put" ? (
            <><Loader2 size={15} className="animate-spin" /> Enviando…</>
          ) : (
            <><ArrowDownRight size={15} /> PUT</>
          )}
        </button>
      </div>

      {feedback && (
        <p
          role={feedback.kind === "error" ? "alert" : "status"}
          className={cn(
            "mt-3 text-xs",
            feedback.kind === "success" ? "text-success" : "text-destructive"
          )}
        >
          {feedback.text}
        </p>
      )}

      <p className="mt-3 text-[11px] leading-relaxed text-muted">
        execução em até 5s · conta PRACTICE · respeita teto de stake
      </p>
    </div>
  );
}
