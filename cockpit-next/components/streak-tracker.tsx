import { cn } from "@/lib/utils";

type StreakTrackerProps = {
  trades: any[];
};

function isWin(trade: any): boolean {
  return parseFloat(trade?.profit) > 0;
}

export function StreakTracker({ trades }: StreakTrackerProps) {
  if (!trades || trades.length === 0) {
    return (
      <div className="bg-surface border border-border rounded-lg p-4">
        <h3 className="text-sm font-medium">Sequências</h3>
        <p className="text-muted text-sm mt-2">Sem trades ainda</p>
      </div>
    );
  }

  // Ordem cronológica: mais antigo -> mais recente
  const chronological = [...trades].reverse();

  // Melhor sequência de wins / pior de losses
  let bestWinStreak = 0;
  let worstLossStreak = 0;
  let runWins = 0;
  let runLosses = 0;

  for (const trade of chronological) {
    if (isWin(trade)) {
      runWins += 1;
      runLosses = 0;
      if (runWins > bestWinStreak) bestWinStreak = runWins;
    } else {
      runLosses += 1;
      runWins = 0;
      if (runLosses > worstLossStreak) worstLossStreak = runLosses;
    }
  }

  // Sequência atual: conta a partir do mais recente (início do array original)
  const lastIsWin = isWin(trades[0]);
  let currentCount = 0;
  for (const trade of trades) {
    if (isWin(trade) === lastIsWin) {
      currentCount += 1;
    } else {
      break;
    }
  }
  const currentLabel = `${currentCount}${lastIsWin ? "W" : "L"}`;

  // Últimos 10 resultados, mais recente à direita
  const last10 = [...trades.slice(0, 10)].reverse();

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <h3 className="text-sm font-medium">Sequências</h3>

      <div className="grid grid-cols-3 gap-2 mt-3">
        <div>
          <p className="text-muted text-xs">Sequência atual</p>
          <p
            className={cn(
              "text-lg font-semibold",
              lastIsWin ? "text-success" : "text-destructive"
            )}
          >
            {currentLabel}
          </p>
        </div>
        <div>
          <p className="text-muted text-xs">Melhor (wins)</p>
          <p className="text-lg font-semibold text-success">
            {bestWinStreak > 0 ? `${bestWinStreak}W` : "—"}
          </p>
        </div>
        <div>
          <p className="text-muted text-xs">Pior (losses)</p>
          <p className="text-lg font-semibold text-destructive">
            {worstLossStreak > 0 ? `${worstLossStreak}L` : "—"}
          </p>
        </div>
      </div>

      <div className="mt-3">
        <p className="text-muted text-xs mb-2">Últimos 10</p>
        <div className="flex items-center gap-1.5">
          {last10.map((trade, index) => {
            const win = isWin(trade);
            return (
              <span
                key={index}
                title={win ? "Win" : "Loss"}
                style={{
                  backgroundColor: win ? "#3DD68C" : "#FF5470",
                  width: 10,
                  height: 10,
                  borderRadius: 9999,
                  display: "inline-block",
                }}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
