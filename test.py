import json
import os
import sys
from datetime import datetime, timezone, timedelta
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("test")

class Cfg:
    DAILY_META_FILE = "test_daily_meta.json"
cfg = Cfg()

def _get_daily_base(current_balance: float) -> float:
    tz_br = timezone(timedelta(hours=-3))
    today_str = datetime.now(tz_br).strftime("%Y-%m-%d")
    
    data = {}
    if os.path.exists(cfg.DAILY_META_FILE):
        try:
            with open(cfg.DAILY_META_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    if data.get("date") == today_str:
        return float(data.get("start_balance", current_balance))
    else:
        data = {
            "date": today_str,
            "start_balance": current_balance
        }
        os.makedirs(os.path.dirname(cfg.DAILY_META_FILE) or ".", exist_ok=True)
        with open(cfg.DAILY_META_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        log.info(f"[JUROS COMPOSTOS] Novo dia iniciado ({today_str}). Base atualizada para {current_balance:.2f}")
        return current_balance

if __name__ == "__main__":
    _get_daily_base(100.0)
    _get_daily_base(150.0)
    print("Done")
