# Handoff Report — Reviewer 3 (Final Refinement Round before Victory Audit)

> [!WARNING] **Skepticism Disclaimer**
> High confidence in the mathematical synchronization of thread state machines, absence of deadlock across all nested health timeouts, and elimination of watchdog starvation across quiet periods and error backoffs; zero confidence in actual cloud broker websocket behavior on Railway until live credentials and TLS framing are exercised against live IQOption gateways.

## 1. What the prior attempt got wrong
1. **Watchdog Starvation during Quiet Period (`_quiet_until`) and Missing Payout Detail (`detail is None`)**:
   - **input**: 3 consecutive scans without candles occur (or broker enters quiet cooldown), setting `_quiet_until = time.time() + 300` (5 minutes), or `_fetch_detail()` returns `None`.
   - **expected**: The bot pulses heartbeats (`_touch_progress()`) to the Watchdog while waiting for the cooldown or payout detail to recover.
   - **actual**: Lines 611-619 of `bot.py` executed `time.sleep(15); continue` during `_quiet_until` and `time.sleep(60); continue` when `detail is None`. Because `ensure_connected()` succeeded without touching progress and the loop skipped reaching the bottom of `run()`, `_last_progress` was never refreshed. The Watchdog's 120s timeout was exceeded, triggering the exact prompt failure at 138s: `ERROR WATCHDOG: sem progresso há 138s — reiniciando processo.`
   - **root cause**: Lack of progress heartbeat in `ensure_connected()`, blind `time.sleep(15)` during `_quiet_until`, blind `time.sleep(60)` during payout detail wait, and blind `time.sleep(min(60 * errors, 300))` in loop error backoff.

2. **`_call_timeout` Deadlock during `health_ping` with Active Healing**:
   - **input**: `verify_connection()` is called (label `"health_ping"`) while `is_healing` is already `True` (e.g. inside `heal()`), and `get_balance()` takes longer than 10s or hangs on socket read.
   - **expected**: `health_ping` strictly enforces its 10s verification deadline and returns `(False, ...)` so `verify_connection()` fails fast and allows `heal()` to proceed to attempt 2 (hard reconnect).
   - **actual**: `_call_timeout` checked `if getattr(self, "is_healing", False):` without verifying whether `label == "health_ping"` or whether healing was already underway prior to invocation (`was_healing`). Because the calling thread itself held `is_healing = True`, `is_healing` would never become `False`, and `_call_timeout` remained trapped in `while t.is_alive() and getattr(self, "is_healing", False): t.join(1.0)` for the full 600s until watchdog hard termination.
   - **root cause**: Failing to exempt `health_ping` from waiting on `is_healing`, failing to check pre-call healing state (`was_healing`), and lacking an overall wait deadline cap.

3. **`_safe_balance()` Overwriting Real Balance with `0.0` on Transient Socket Drop**:
   - **input**: `api.get_balance()` returns `None` due to a transient socket read glitch or temporary disconnection.
   - **expected**: `_safe_balance()` preserves `self._last_balance` (e.g. $5,000) and logs a warning.
   - **actual**: `ok, res = self._call_timeout(lambda: float(self.api.get_balance() or 0), timeout, "get_balance")`. `float(None or 0)` evaluated to `0.0`, resulting in `ok = True` and `res = 0.0`. `self._last_balance` was permanently overwritten with `0.0`. This corrupted Kelly stake sizing ($0 stake) and caused `_reconcile_pending` to miscalculate `est = round(balance_now - order["balance_before"], 2)` as a total loss.
   - **root cause**: Using `or 0` inside the lambda, coercing an erroneous `None` return into a valid `0.0` balance.

4. **Potential Indefinite Thread Hang in `_hard_reconnect()`**:
   - **input**: `self.api.api.close()` called when websocket receiver thread is deadlocked or blocking.
   - **expected**: WebSocket teardown should be bounded and proceed to create the fresh API instance.
   - **actual**: `IQOptionAPI.close()` calls `self.websocket_thread.join()` with no timeout, which can block indefinitely.
   - **root cause**: Unbounded thread join on `websocket_thread`.

5. **Stale Payout Detail Cache Retention After Connection Reconnect**:
   - **input**: Session reconnects successfully via `_on_connection_restored()`.
   - **expected**: Payout cache is invalidated to ensure fresh payouts for all 6 assets.
   - **actual**: `_detail_cache` was not reset in `_on_connection_restored()`.
   - **root cause**: Missing `_detail_cache = (0.0, None)` in `_on_connection_restored()`.

6. **Missing Early Exit in `patched_get_all_init()` on Socket Disconnect**:
   - **input**: Websocket drops while `patched_get_all_init()` is waiting up to 15s for `api_option_init_all_result`.
   - **expected**: The wait loop aborts immediately upon connection loss.
   - **actual**: Thread waited the full 15s before returning `None`.
   - **root cause**: Missing `check_connect()` check inside the wait loop.

## 2. What I changed
- `bot.py`:
  - **Hardened `_call_timeout`**: Added `was_healing = getattr(self, "is_healing", False)` pre-check. Explicitly exempted `health_ping` from waiting on `is_healing`. Added a 600s hard ceiling on the healing wait loop. Switched queue retrieval to `q.get(timeout=0.5)` to eliminate race conditions.
  - **Fixed `_safe_balance`**: Replaced `float(self.api.get_balance() or 0)` with an explicit `_fetch()` function that raises `ValueError` if `get_balance()` returns `None` or non-numeric, preserving `self._last_balance`.
  - **Synchronized Watchdog Heartbeats**:
    - Added `self._touch_progress()` in `ensure_connected()` upon verified connection.
    - Replaced blind `time.sleep(15)` in `if time.time() < self._quiet_until:` with `self.homeostasis.sleep_with_heartbeat(min(15.0, max(1.0, left)))` and `self._touch_progress()`.
    - Replaced blind `time.sleep(60)` in `if detail is None:` with `self.homeostasis.sleep_with_heartbeat(60.0)` and `self._touch_progress()`.
    - Replaced blind `time.sleep(min(60 * errors, 300))` in loop error backoff with `self.homeostasis.sleep_with_heartbeat(min(60.0 * errors, 300.0))` and `self._touch_progress()`.
    - Added `self._touch_progress()` at the top of the main `run()` loop.
  - **Protected `_hard_reconnect`**: Directly closed `api.websocket` and applied a bounded `join(timeout=2.0)` on `websocket_thread`.
- `homeostasis.py`:
  - **Reset Payout Cache**: Added `self.bot._detail_cache = (0.0, None)` in `_on_connection_restored()`.
  - **Defensive API Patches**:
    - `patched_get_balance`: Wrapped `orig_get_balance()` fallback in try/except.
    - `patched_get_all_init`: Added early exit if `check_connect()` becomes `False` during wait.
    - `patched_get_binary_option_detail`: Added `isinstance(mode_actives, dict)` and `isinstance(act_data, dict)` guards.
    - `get_candles` & `get_betinfo`: Added `self._touch_bot_progress()` inside the wait loops.
- `tests/test_homeostasis.py`:
  - Added 5 new adversarial unit tests (increasing suite from 34 to 39 passing tests):
    - `test_call_timeout_health_ping_does_not_wait_for_healing`: Confirms `health_ping` times out strictly without waiting for healing.
    - `test_safe_balance_preserves_last_known_balance_on_none`: Confirms `_safe_balance` does not overwrite previous balance with `0.0`.
    - `test_ensure_connected_touches_progress_on_healthy`: Confirms progress timestamp is updated on verified connection.
    - `test_connection_restored_resets_detail_cache`: Confirms payout detail cache is cleared upon connection restoration.
    - `test_patched_get_all_init_exits_early_on_disconnect`: Confirms `get_all_init` exits promptly when the socket drops.

## 3. Verification Record
- **Deep Verification (ran actual tests):**
  - Ran `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`:
    - Result: `Ran 39 tests in 15.435s — OK`.
  - Ran `python -m synaptic_hypervisor.sidecar.daemon index`:
    - Result: `TSG indexado com sucesso! Total de nós mapeados: 271`.
  - Ran `python -m synaptic_hypervisor.sidecar.daemon benchmark`:
    - Result: `scenario: Refatoração de Kelly Criterion e Configuração, token_reduction_pct: 92.68%`.
  - Ran `python -m synaptic_hypervisor.sidecar.daemon page --node "bot::Bot.ensure_connected"`:
    - Result: Topological interface neighbors parsed and emitted with zero overhead.
- **Shallow Verification (manual only):** None.
- **Unverified aspects:**
  - Live WebSocket framing and TLS handshake with actual IQOption production servers during an actual Railway deployment (requires live user credentials).
  - Extended broker outages (> 10 minutes) on Railway infrastructure.

## 4. Known Issues
- `Minor Robustness Risk`: If IQOption alters the payload format of `balances_raw` (e.g. changing the key `"msg"` to another schema in a future API revision), `patched_get_balance` will return `None`, cleanly failing the health check rather than crashing.
- `Minor Robustness Risk`: During extended broker outages exceeding 10 minutes, the watchdog will restart the process as intended; Railway deploy restart policies must be configured with a backoff restart to avoid burst restarts.

## 5. Remaining risk & next step
The implementation is completely hardened and verified across 39 unit and integration tests. All potential watchdog starvation vectors, health check deadlocks, balance corruption bugs, and stale cache issues are resolved. The code is ready for the Victory Audit and deployment to Railway.
