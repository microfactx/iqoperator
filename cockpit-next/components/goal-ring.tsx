"use client";

import { Target } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";

type GoalRingProps = {
  session: number;
  stopWin?: number;
  stopLoss?: number;
};

const TRACK_COLOR = "#232A36";
const PROFIT_COLOR = "#3DD68C";
const LOSS_COLOR = "#FF5470";

function formatSigned(value: number): string {
  const fixed = Math.abs(value).toFixed(2);
  return value >= 0 ? `+${fixed}` : `-${fixed}`;
}

export function GoalRing({ session, stopWin = 50, stopLoss = 30 }: GoalRingProps) {
  const isProfit = session >= 0;

  const safeStopWin = stopWin > 0 ? stopWin : 50;
  const safeStopLoss = stopLoss > 0 ? stopLoss : 30;

  const fraction = isProfit
    ? Math.min(Math.max(session / safeStopWin, 0), 1)
    : Math.min(Math.max(Math.abs(session) / safeStopLoss, 0), 1);

  const progressColor = isProfit ? PROFIT_COLOR : LOSS_COLOR;
  const data = [
    { name: "progresso", value: fraction },
    { name: "trilha", value: 1 - fraction },
  ];

  const centerLabel = isProfit
    ? `${formatSigned(session)} / +${safeStopWin.toFixed(2)}`
    : `${formatSigned(session)} / -${safeStopLoss.toFixed(2)}`;

  const distanceLabel = isProfit
    ? `Faltam ${Math.max(safeStopWin - session, 0).toFixed(2)} para o stop-win`
    : `Margem de ${Math.max(safeStopLoss - Math.abs(session), 0).toFixed(2)} até o stop-loss`;

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center gap-2"><Target size={14} className="text-muted" /><h3 className="text-sm font-medium">Meta da sessão</h3></div>

      <div className="relative h-[180px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={60}
              outerRadius={80}
              startAngle={90}
              endAngle={-270}
              stroke="none"
              isAnimationActive={false}
            >
              <Cell fill={progressColor} />
              <Cell fill={TRACK_COLOR} />
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={cn(
              "text-sm font-medium tabular-nums",
              isProfit ? "text-success" : "text-destructive"
            )}
          >
            {centerLabel}
          </span>
          <span className="text-xs text-muted tabular-nums">
            {isProfit
              ? `${((session / safeStopWin) * 100).toFixed(1)}% da meta`
              : `${((Math.abs(session) / safeStopLoss) * 100).toFixed(1)}% do limite`}
          </span>
        </div>
      </div>

      <p className="mt-2 text-center text-xs text-muted">{distanceLabel}</p>
    </div>
  );
}
