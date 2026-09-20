# H010 — Plano de backtest independente (a executar depois)

Modelo: `MODEL_H010_BTCUSDT_ORDERFLOW_ABSORPTION` (spec em `hypothesis.json`).
Objetivo: replicar de forma independente o backtest OOS (153 dias, N=147, WR 62.6%)
com nosso pipeline, antes de qualquer execução.

## 1. O que o setup exige (lido dos parâmetros)

- **Macro (1440m ≈ 1 dia):** referência de preço; entrada só com esticada
  `>= 1.5 × ATR(14)` da referência, tolerância `±1.5%`.
- **Micro (1m + 5s):** pavio (wick) >= 35% do range do candle + absorção de fluxo
  (lado contrário >= 45% do volume) + timing de entrada <= 50s.
- **Expiração:** 60s (1 candle M1), direção = reversão (fade da esticada).
- **Payout ref:** 0.85 → breakeven 54.05%.

> Interpretação nossa a partir dos nomes/valores — o código-fonte
> (`OrderFlowAbsorptionModel.js`) não está neste repo. Para réplica exata,
> importar a lógica dele ou confirmar cada fórmula antes de rodar.

## 2. Dados necessários (não temos ainda)

| Dado | Fonte | Volume aprox. 153 dias |
|---|---|---|
| Candles 1m BTCUSDT | REST Binance ou ZIP mensal | ~220k linhas (leve) |
| Micro 5s (ou 1s → agregar) | `data.binance.vision` ZIPs diários `1s` | ~153 arquivos |
| Fluxo taker buy/sell (absorção) | `aggTrades` ZIPs diários | dezenas de GB (pesado) |

Sem o fluxo taker não há como aplicar o filtro `absorptionShare >= 0.45`;
o esqueleto (esticada + pavio) dá para testar só com candles — ver §4.

## 3. Gate de aceitação (mesmo padrão anti-ilusão do repo)

1. N >= 100 sinais no OOS (setup raro: o original teve 147).
2. Limite inferior de Wilson 95% do WR > breakeven do payout testado.
3. Lucro nas duas metades do período.
4. Controle negativo: versão invertida (mesma lógica, direção oposta) deve dar WR < 50%.

## 4. Caminho em 2 fases

- **Fase A (barata, fazível já):** esqueleto stretch + wick em M1, sem absorção.
  Se o esqueleto sozinho já der ~50%, o filtro de absorção é o edge alegado —
  aí vale investir no download pesado.
- **Fase B (cara):** pipeline 5s + aggTrades + réplica fiel + gates acima.

## 5. Notas de execução IQOption (se validar)

Expiração 60s existe na binária; payout BTC raramente é 0.85 fixo —
usar `PAYOUT_MIN` travado e auditar payout real por trade no `trades_live.csv`.
Latência de entrada (< 250ms no spec) é o maior risco de fidelidade no bot atual.
