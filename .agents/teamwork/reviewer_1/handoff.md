# Handoff Report — Reviewer 1 (Adversarial Review & Fixes)

> [!WARNING] **Skepticism Disclaimer**
> Confidence is high on concurrency synchronization, socket error discrimination, and local state mechanics; zero confidence regarding undocumented broker-side protocol mutations on Railway until live credentials are validated in the cloud container.

## 1. What the prior attempt got wrong
1. **Unmapped Asset Reconnect Loop (`AUDUSD-OTC`, `USDCAD-OTC`)**:
   - **input**: Asset name not statically present in `OP_code.ACTIVES` (e.g. `AUDUSD-OTC` or `USDCAD-OTC` in `DEFAULT_ASSETS`).
   - **expected**: Asset should be resolved dynamically via broker opcodes or skipped gracefully without triggering false reconnects.
   - **actual**: `int(active_id)` failed with `ValueError: invalid literal for int() with base 10: 'AUDUSD-OTC'`. The exception handler caught this and triggered `self.heal()`. Because the asset remained unmapped on the next polling cycle, this produced an infinite loop of reconnects every cycle.
   - **root cause**: `homeostasis.py` assumed `OP_code.ACTIVES.get(actives, actives)` would work directly with `api.getcandles`, but the underlying `GetCandles` channel executes `int(active_id)`. Furthermore, `bot.py` never called `update_ACTIVES_OPCODE` upon connecting.
2. **Candle Timeout Silently Dropped without Healing**:
   - **input**: `api.get_candles` times out because the IQOption websocket stopped delivering candles.
   - **expected**: `get_candles` should recognize the connection failure, log `**error** get_candles need reconnect`, and trigger `heal()`.
   - **actual**: `get_candles` returned `None` without triggering `heal()`. In `bot.py`, `_call_timeout` received `None` successfully (`ok=True`), bypassing `if not ok:` and treating the timeout as an empty candle ("vazio"), leaving `if "timeout" in str(res).lower(): self.homeostasis.heal(...)` as dead code.
   - **root cause**: Asymmetry between `get_betinfo` (which called `heal()` on timeout) and `get_candles` (which only logged a warning and returned `None`).
3. **Lock Contention and Deadlock Risk in `heal()`**:
   - **input**: Multiple threads invoking `self.homeostasis.heal()` concurrently (e.g. timeout worker and main thread).
   - **expected**: Fast state checking where concurrent callers wait on `threading.Event`, while the healing thread executes backoff sleeps.
   - **actual**: The entire backoff loop (up to 10 attempts and minutes of sleep) was executed inside `with self._lock:`. Any concurrent thread attempting to enter `heal()` was blocked on `_lock.acquire()` without timeout instead of waiting on `_healing_event`.
   - **root cause**: Holding a mutex across multi-minute I/O and sleep operations instead of using check-and-set state protection.
4. **Websocket Resource Leak on Hard Reconnect**:
   - **input**: `Bot._hard_reconnect()` recreating the API instance.
   - **expected**: Underlying websocket and worker thread terminated cleanly.
   - **actual**: Code attempted `self.api.websocket_client.close()`, which raised `AttributeError` (ignored by `try/except`), leaving the old websocket thread in `self.api.api.websocket` orphaned and leaking resources.
   - **root cause**: Incorrect attribute lookup (`websocket_client` vs `api.close()`).
5. **Premature Main Loop Execution during Healing**:
   - **input**: Main loop calling `self.ensure_connected()` while a background healing cycle was already running.
   - **expected**: `ensure_connected` should wait for the healing cycle to conclude and verify the connection.
   - **actual**: `ensure_connected` returned `True` immediately (`if getattr(self, "is_healing", False): return True`), causing the main loop to continue into scanning and trading while the connection was dead.
   - **root cause**: Conflating "healing is active" with "connection is healthy".
6. **Watchdog Indefinite Hang Bypass**:
   - **input**: Application hanging or deadlocking permanently inside the IQOption library (e.g., `while global_value.balance_id == None: pass`).
   - **expected**: Watchdog should enforce a hard maximum duration for healing (e.g., 600s) and restart the container if stuck.
   - **actual**: Watchdog unconditionally reset `_last_progress` on every 30s check whenever `is_healing` was True, effectively neutering the watchdog forever.
   - **root cause**: Lack of an upper bound on `is_healing` duration.
7. **100% CPU Busy-Spin in `get_balances`**:
   - **input**: Websocket latency or disconnection during balance queries.
   - **expected**: Bounded wait with sleep chunking.
   - **actual**: `IQ_Option.get_balances` spun at 100% CPU in `while self.api.balances_raw == None: pass`.
   - **root cause**: Unpatched `get_balances` method in the underlying library.

## 2. What I changed
- `homeostasis.py`:
  - Refactored `HomeostasisManager.heal`: `_lock` is now held strictly for atomic state transition (check-and-set). Backoff loop and sleeps occur outside the lock. Concurrent threads await `_healing_event` with bounded timeout.
  - Added `_healing_started_ts` tracking for watchdog timeout protection.
  - Updated `get_candles`:
    - Added opcode resolution: handles unmapped assets, checks `OP_code.ACTIVES`, attempts `update_ACTIVES_OPCODE()`, and skips unmapped assets without triggering false reconnects.
    - Added socket exception discrimination: ignores parameter errors (`ValueError`, `TypeError`), triggers `heal()` on network/socket disconnects.
    - Added timeout trigger: logs `**error** get_candles need reconnect` and invokes `self.heal()` when candle delivery times out.
  - Patched `api.get_balances` in `patch_api` to eliminate 100% CPU busy-wait spinning (`while balances_raw == None: pass`).
  - Added reset of `_last_balance` and `_balance_ts` in `_on_connection_restored`.
- `bot.py`:
  - Updated `_start_watchdog`: Added 600s hard timeout cap on `is_healing` via `_healing_started_ts` to prevent permanent container freeze.
  - Updated `connect()`: Calls `update_ACTIVES_OPCODE()` upon successful connect.
  - Updated `ensure_connected()`: When `is_healing` is True, delegates to `self.homeostasis.heal()` to wait for healing completion instead of blindly returning True. Exits cleanly with `os._exit(1)` if healing fails after all 10 attempts in `run()`.
  - Updated `_hard_reconnect()`: Correctly invokes `self.api.api.close()` to close sockets and join threads cleanly.
  - Updated `candles_df()` and `_poll_pending()`: Passes `timeout` properly to API calls with buffer in `_call_timeout`.
- `tests/test_homeostasis.py`:
  - Added 6 adversarial test cases covering unmapped asset handling, candle timeout triggering heal, lock release during backoff, `ensure_connected` waiting for healing, watchdog stuck-healing termination, and `get_balances` bounded wait.

## 3. Verification Record
- **Deep Verification (ran actual tests):**
  - Ran `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`: All 27 tests passed (21 unit tests in test_homeostasis + 6 hypervisor integration tests) in 9.791s.
  - Ran `DeterministicSandbox.check_python_syntax` on `homeostasis.py` and `bot.py`: Returned `SYNTAX_OK`.
  - Ran `synaptic_hypervisor.sidecar.daemon index`: 259 nodes successfully mapped into TSG.
- **Shallow Verification (manual only):**
  - Code review of diff across `homeostasis.py`, `bot.py`, `config.py`.
- **Unverified aspects:**
  - Real live network exchange with IQOption production TLS WebSocket endpoints in Railway (unverifiable locally without live user credentials).

## 4. Known Issues
- `Minor Robustness Risk`: If IQ Option upstream deprecates `getcandles` or websocket channels in an API version increment, dynamic opcodes would need re-inspection.
- `Minor Robustness Risk`: During extended broker outages exceeding 10 minutes, the watchdog will restart the process as intended; Railway deploy restart policies must be configured with a backoff restart to avoid burst restarts.

## 5. Remaining risk & next step
The implementation is solid and mathematically sound with 27 passed unit and adversarial tests. The next step is deployment to Railway with live telemetry monitoring.
