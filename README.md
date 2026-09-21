# Robô IQOption — BTCUSD Binárias

Base em Python com `iqoptionapi` (não-oficial, para estudo).

> Aviso: API não-oficial, pode quebrar. Nunca teste direto na conta REAL. Use `PRACTICE`.

## 1. Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edite o .env com seu email/senha
python main.py
```

## 2. Arquivos

- `config.py` — lê tudo do `.env`
- `strategies.py` — `rsi_m15` (RSI 14 reversão: CALL ao sair do oversold, PUT ao sair do overbought)
- `kelly.py` — Kelly fracionário com teto de 2% da banca
- `bot.py` — conexão, filtro payout, stake via Kelly, stop win/loss
- `main.py` — entrypoint

## 3. Kelly (KELLY_PRIOR + fração)

- Breakeven p/ payout 0.80 = `1/1.8 = 55.56%`. Por isso `KELLY_PRIOR=0.58` (edge pequeno, conservador).
- `KELLY_FRACTION=0.25` = quarter-Kelly. Ex: banca 1000, `p=0.58`, `b=0.8` → `f*=5.5%` → stake `1000*5.5%*0.25 = 13.75` (teto 2% = 20).
- Winrate bayesiano: `(prior*20 + wins)/(20 + n)` — prior domina no início, empírico assume após ~50 trades.

## 5. Forward test em DEMO (2–3 meses)

Setup travado pelo backtest 1y: `rsi_mtf_pullback` (viés H1 EMA50 + RSI14 M15 em zona),
Kelly quarter com teto 2%. **Não trocar parâmetros durante o teste.**

```powershell
pip install -r requirements.txt
copy .env.example .env
# edite .env: IQ_EMAIL, IQ_PASSWORD, IQ_BALANCE_TYPE=PRACTICE
py main.py
```

- O bot só opera em `PRACTICE` (conta REAL exige `CONFIRM_REAL=YES` e aborta sem ela).
- Logs: `bot.log` + cada trade em `data/trades_live.csv` (hora, sinal, RSI, payout, stake, lucro).
- Reconexão automática; filtros: payout mínimo e 1 trade por candle novo.
- Precisa do PC ligado 24/7 (ou VPS). BTC fecha fds? Opera `BTCUSD-OTC` se configurado.
- Avaliação ao final: comparar WR e lucro com o backtest (`--split`).
