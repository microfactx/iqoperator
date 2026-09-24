"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { cn } from "@/lib/utils";
import { ChartTooltip } from "@/components/ui/chart-tooltip";

type SignalDistributionProps = {
  trades: any[];
};

type SignalSlice = {
  name: "CALL" | "PUT";
  value: number;
};

const CALL_COLOR = "#3DD68C";
const PUT_COLOR = "#FF5470";

function isWin(profit: unknown): boolean {
  return parseFloat(String(profit)) > 0;
}

function normalizeSignal(signal: unknown): "call" | "put" | null {
  if (typeof signal !== "string") return null;
  const s = signal.toLowerCase();
  if (s === "call") return "call";
  if (s === "put") return "put";
  return null;
}

function formatWinrate(wins: number, total: number): string {
  if (total === 0) return "— (0/0)";
  const pct = ((wins / total) * 100).toFixed(1);
  return `${pct}% (${wins}/${total})`;
}

export function SignalDistribution({ trades }: SignalDistributionProps) {
  const list = Array.isArray(trades) ? trades : [];

  let calls = 0;
  let puts = 0;
  let callWins = 0;
  let putWins = 0;

  for (const t of list) {
    const sig = normalizeSignal(t?.signal);
    if (sig === "call") {
      calls += 1;
      if (isWin(t?.profit)) callWins += 1;
    } else if (sig === "put") {
      puts += 1;
      if (isWin(t?.profit)) putWins += 1;
    }
  }

  const total = calls + puts;

  const data: SignalSlice[] = [
    { name: "CALL", value: calls },
    { name: "PUT", value: puts },
  ];

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <h3 className="text-sm font-medium">Distribuição de sinais</h3>

      {total === 0 ? (
        <div className="flex h-[220px] w-full items-center justify-center">
          <p className="text-sm text-muted">Sem sinais ainda</p>
        </div>
      ) : (
        <>
          <div className="relative h-[220px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip
                  content={
                    <ChartTooltip
                      hideLabel
                      valueFormatter={(value) => `${value} sinais`}
                    />
                  }
                />
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={2}
                  stroke="none"
                  isAnimationActive={false}
                >
                  <Cell fill={CALL_COLOR} />
                  <Cell fill={PUT_COLOR} />
                </Pie>
              </PieChart>
            </ResponsiveContainer>

            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-semibold tabular-nums">{total}</span>
              <span className="text-xs text-muted">
                {total === 1 ? "sinal" : "sinais"}
              </span>
            </div>
          </div>

          <div className="mt-2 space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-2">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: CALL_COLOR }}
                />
                <span className="text-muted">CALL</span>
              </span>
              <span className={cn("font-medium tabular-nums text-success")}>
                {formatWinrate(callWins, calls)}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-2">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: PUT_COLOR }}
                />
                <span className="text-muted">PUT</span>
              </span>
              <span className={cn("font-medium tabular-nums text-destructive")}>
                {formatWinrate(putWins, puts)}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
