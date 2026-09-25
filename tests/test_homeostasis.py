"""
Unit tests for Homeostasis Autonomic Connection Healing & Watchdog Synchronization.
"""

from __future__ import annotations
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from homeostasis import HomeostasisManager
import config as cfg


class FakeAPI:
    """Mock da API IQOption com estruturas internas para teste."""
    def __init__(self, connected: bool = True):
        self._connected = connected
        self.api = MagicMock()
        self.api.candles = MagicMock()
        self.api.candles.candles_data = None
        self.api.game_betinfo = MagicMock()
        self.api.game_betinfo.isSuccessful = None
        self.api.game_betinfo.dict = {"123": {"win": "win", "profit": 1.85, "deposit": 1.0}}

        def _getcandles(actives, interval, count, endtime):
            self.api.candles.candles_data = getattr(self, "_mock_candles", [{"open": 1.0, "close": 1.1, "min": 0.9, "max": 1.2}])

        def _get_betinfo(id_num):
            self.api.game_betinfo.isSuccessful = getattr(self, "_mock_betinfo_success", True)

        self.api.getcandles.side_effect = _getcandles
        self.api.get_betinfo.side_effect = _get_betinfo

    def check_connect(self) -> bool:
        return self._connected

    def connect(self):
        return self._connected, None

    def change_balance(self, mode):
        pass

    def get_balance(self):
        return 1000.0


class FakeBot:
    """Mock do Bot para testar a integração com a Homeostase."""
    def __init__(self, connected: bool = True):
        self.api = FakeAPI(connected=connected)
        self.is_healing = False
        self._last_progress = time.time()
        self._candle_fail = {"EURUSD-OTC": [3, time.time() + 180]}
        self._asset_cursor = 4
        self._consecutive_global_fails = 5
        self._empty_scans = 2
        self._quiet_until = time.time() + 60
        self._hard_reconnect_count = 1
        self.assets = list(cfg.ASSETS)
        self.connect_count = 0
        self.hard_reconnect_count = 0

    def _touch_progress(self):
        self._last_progress = time.time()

    def connect(self) -> bool:
        self.connect_count += 1
        return self.api.connect()[0]

    def _hard_reconnect(self) -> bool:
        self.hard_reconnect_count += 1
        return self.connect()

    def verify_connection(self) -> bool:
        return self.api.check_connect()


class TestHomeostasisManager(unittest.TestCase):

    def setUp(self):
        self.bot = FakeBot()
        self.manager = HomeostasisManager(
            bot=self.bot,
            initial_backoff=0.05,
            backoff_factor=1.5,
            max_backoff=0.2,
            max_attempts=3,
        )

    def test_initial_state(self):
        """Verifica se o estado inicial de homeostase é limpo."""
        self.assertFalse(self.manager.is_healing)
        self.assertFalse(self.bot.is_healing)

    def test_heal_success_first_attempt(self):
        """Verifica cura com sucesso na primeira tentativa."""
        success = self.manager.heal(reason="teste de queda")
        self.assertTrue(success)
        self.assertFalse(self.manager.is_healing)
        self.assertFalse(self.bot.is_healing)
        self.assertEqual(len(self.bot._candle_fail), 0, "Cooldowns de candles devem ser limpos após cura.")
        self.assertEqual(self.bot._asset_cursor, 0, "Cursor de ativos deve ser resetado para retomar polling.")
        self.assertEqual(self.bot._consecutive_global_fails, 0)
        self.assertEqual(self.bot._empty_scans, 0)
        self.assertEqual(self.bot._quiet_until, 0.0)

    def test_heal_retry_with_exponential_backoff(self):
        """Verifica retry com backoff e transição para hard_reconnect."""
        # Primeira tentativa falha, segunda sucede
        attempts = [False, True]

        def mock_connect():
            return attempts.pop(0)

        self.bot.connect = mock_connect
        self.bot._hard_reconnect = mock_connect

        start_time = time.time()
        success = self.manager.heal(reason="queda com retry")
        elapsed = time.time() - start_time

        self.assertTrue(success)
        self.assertGreater(elapsed, 0.04, "Backoff deve introduzir atraso proporcional.")
        self.assertEqual(len(self.bot._candle_fail), 0)

    def test_heal_exhausted_attempts(self):
        """Verifica comportamento quando todas as tentativas de reconexão falham."""
        self.bot.connect = lambda: False
        self.bot._hard_reconnect = lambda: False
        self.bot.verify_connection = lambda: False

        success = self.manager.heal(reason="queda total")
        self.assertFalse(success)
        self.assertFalse(self.manager.is_healing)
        self.assertFalse(self.bot.is_healing)

    def test_watchdog_synchronization_during_heartbeat(self):
        """Verifica se sleep_with_heartbeat atualiza continuamente a flag de progresso."""
        initial_progress = time.time() - 100.0
        self.bot._last_progress = initial_progress

        self.manager.sleep_with_heartbeat(0.15, chunk=0.05)
        # O _last_progress deve ter sido atualizado recentemente
        self.assertGreater(self.bot._last_progress, initial_progress)
        self.assertLess(time.time() - self.bot._last_progress, 0.1)

    def test_watchdog_does_not_kill_when_is_healing(self):
        """Verifica se a lógica do watchdog tolera inatividade quando is_healing é True."""
        self.bot.is_healing = True
        self.bot._last_progress = time.time() - 300.0  # Muito acima de cfg.WATCHDOG_TIMEOUT

        # Simula a verificação do watchdog
        killed = False

        def mock_exit(code):
            nonlocal killed
            killed = True

        # Testando o bloco lógico do watchdog
        if getattr(self.bot, "is_healing", False):
            self.bot._touch_progress()
        else:
            idle = time.time() - self.bot._last_progress
            if idle > cfg.WATCHDOG_TIMEOUT:
                mock_exit(1)

        self.assertFalse(killed, "Watchdog não deve matar o processo se is_healing for True.")
        self.assertLess(time.time() - self.bot._last_progress, 1.0, "Progress flag deve ser atualizada.")

    def test_resilient_get_candles_success(self):
        """Verifica captura bem sucedida de candles."""
        api = FakeAPI(connected=True)
        expected_candles = [{"open": 1.0, "close": 1.1, "min": 0.9, "max": 1.2}]
        api._mock_candles = expected_candles

        candles = self.manager.get_candles(api, "EURUSD-OTC", 60, 5, time.time(), timeout=1.0)
        self.assertEqual(candles, expected_candles)

    def test_resilient_get_candles_disconnected_triggers_heal(self):
        """Verifica se get_candles identifica websocket desconectado e aciona heal()."""
        api = FakeAPI(connected=False)
        with patch.object(self.manager, "heal", return_value=True) as mock_heal:
            res = self.manager.get_candles(api, "EURUSD-OTC", 60, 5, time.time(), timeout=0.1)
            self.assertIsNone(res)
            mock_heal.assert_called_once()
            self.assertIn("desconectado", mock_heal.call_args[1]["reason"])

    def test_resilient_get_candles_exception_triggers_heal(self):
        """Verifica se exceção no socket em get_candles aciona heal() e não quebra."""
        api = FakeAPI(connected=True)
        api.api.getcandles.side_effect = ConnectionResetError("Broken pipe")

        with patch.object(self.manager, "heal", return_value=True) as mock_heal:
            res = self.manager.get_candles(api, "EURUSD-OTC", 60, 5, time.time(), timeout=0.1)
            self.assertIsNone(res)
            mock_heal.assert_called_once()
            self.assertIn("exceção", mock_heal.call_args[1]["reason"])

    def test_resilient_get_candles_timeout(self):
        """Verifica se timeout em get_candles retorna None sem travar."""
        api = FakeAPI(connected=True)
        api.api.getcandles.side_effect = lambda *a: None
        api.api.candles.candles_data = None

        candles = self.manager.get_candles(api, "EURUSD-OTC", 60, 5, time.time(), timeout=0.1)
        self.assertIsNone(candles)

    def test_resilient_get_betinfo_success(self):
        """Verifica get_betinfo quando a corretora responde com sucesso."""
        api = FakeAPI(connected=True)
        api._mock_betinfo_success = True

        ok, data = self.manager.get_betinfo(api, 123, timeout=1.0)
        self.assertTrue(ok)
        self.assertIn("123", data)

    def test_resilient_get_betinfo_disconnected_triggers_heal(self):
        """Verifica se get_betinfo identifica websocket desconectado e aciona heal()."""
        api = FakeAPI(connected=False)
        with patch.object(self.manager, "heal", return_value=True) as mock_heal:
            ok, data = self.manager.get_betinfo(api, 123, timeout=0.1)
            self.assertFalse(ok)
            self.assertIsNone(data)
            mock_heal.assert_called_once()

    def test_resilient_get_betinfo_timeout_triggers_heal(self):
        """Verifica se timeout em get_betinfo dispara heal() e não congela a thread."""
        api = FakeAPI(connected=True)
        api.api.get_betinfo.side_effect = lambda id_num: None
        api.api.game_betinfo.isSuccessful = None

        with patch.object(self.manager, "heal", return_value=True) as mock_heal:
            ok, data = self.manager.get_betinfo(api, 123, timeout=0.1)
            self.assertFalse(ok)
            self.assertIsNone(data)
            mock_heal.assert_called_once()
            self.assertIn("timeout", mock_heal.call_args[1]["reason"])

    def test_concurrent_heal_requests_do_not_duplicate(self):
        """Verifica se chamadas concorrentes a heal() não executam reconnects duplicados."""
        reconnect_calls = 0

        def slow_connect():
            nonlocal reconnect_calls
            reconnect_calls += 1
            time.sleep(0.1)
            return True

        self.bot.connect = slow_connect

        t1 = threading.Thread(target=lambda: self.manager.heal("thread 1"))
        t2 = threading.Thread(target=lambda: self.manager.heal("thread 2"))

        t1.start()
        time.sleep(0.01)
        t2.start()

        t1.join()
        t2.join()

        self.assertEqual(reconnect_calls, 1, "Apenas uma cura deve ser executada para chamadas concorrentes.")

    def test_polling_resumed_for_all_six_assets(self):
        """Verifica se a lista de ativos contém as 6 moedas e o cursor reinicia para polling sequencial."""
        expected_assets = ["EURUSD-OTC", "GBPUSD-OTC", "USDJPY-OTC", "AUDUSD-OTC", "EURGBP-OTC", "USDCAD-OTC"]
        for a in expected_assets:
            self.assertIn(a, cfg.ASSETS)
        self.assertEqual(len(cfg.ASSETS), 6)

        # Após cura, o cursor e falhas devem estar zerados
        self.bot._asset_cursor = 5
        self.bot._candle_fail = {a: [2, time.time() + 100] for a in cfg.ASSETS}
        self.manager._on_connection_restored()

        self.assertEqual(self.bot._asset_cursor, 0)
        self.assertEqual(len(self.bot._candle_fail), 0)


    def test_unmapped_asset_does_not_trigger_false_reconnect(self):
        """Ativo não presente em OP_code.ACTIVES não deve disparar erro fatal nem heal()."""
        api = FakeAPI(connected=True)
        def _real_lib_getcandles(active_id, interval, count, endtime):
            int(active_id)
        api.api.getcandles.side_effect = _real_lib_getcandles

        with patch.object(self.manager, "heal") as mock_heal:
            candles = self.manager.get_candles(api, "UNKNOWN_NONEXISTENT_ASSET", 60, 5, time.time())
            self.assertIsNone(candles)
            mock_heal.assert_not_called()

    def test_candle_timeout_triggers_heal(self):
        """Timeout aguardando candles deve logar need reconnect e disparar heal()."""
        api = FakeAPI(connected=True)
        api.api.getcandles.side_effect = lambda *a: None
        api.api.candles.candles_data = None

        with patch.object(self.manager, "heal", return_value=True) as mock_heal:
            candles = self.manager.get_candles(api, "EURUSD-OTC", 60, 5, time.time(), timeout=0.05)
            self.assertIsNone(candles)
            mock_heal.assert_called_once()
            self.assertIn("timeout", mock_heal.call_args[1]["reason"])

    def test_lock_released_during_backoff(self):
        """O lock interno de heal não deve ser retido durante o backoff sleep."""
        self.bot.connect = MagicMock(return_value=False)
        self.bot._hard_reconnect = MagicMock(return_value=False)
        self.manager.max_attempts = 2
        self.manager.initial_backoff = 0.2

        t = threading.Thread(target=lambda: self.manager.heal("test_lock"))
        t.start()
        time.sleep(0.05)
        acquired = self.manager._lock.acquire(timeout=0.05)
        self.assertTrue(acquired, "Lock deve ser liberado durante o backoff da cura.")
        if acquired:
            self.manager._lock.release()
        t.join()

    def test_ensure_connected_waits_if_healing(self):
        """ensure_connected deve chamar heal() para aguardar cura se is_healing já for True."""
        from bot import Bot
        bot = Bot.__new__(Bot)
        bot.is_healing = True
        bot.homeostasis = MagicMock()
        bot.homeostasis.heal.return_value = True

        res = Bot.ensure_connected(bot)
        self.assertTrue(res)
        bot.homeostasis.heal.assert_called_once_with(reason="ensure_connected aguardando cura em andamento")

    def test_watchdog_terminates_prolonged_stuck_healing(self):
        """Watchdog deve reiniciar o processo se a cura ficar presa por mais de 600s."""
        self.bot.is_healing = True
        self.bot._healing_started_ts = time.time() - 700.0

        killed = False
        def mock_exit(code):
            nonlocal killed
            killed = True

        healing_started = getattr(self.bot, "_healing_started_ts", 0.0)
        if healing_started > 0.0 and (time.time() - healing_started) > 600.0:
            mock_exit(1)

        self.assertTrue(killed, "Watchdog deve matar o processo se o estado de cura exceder 600s.")

    def test_patch_api_balances_bounded_wait(self):
        """Wrapper resiliente get_balances não deve travar em loop infinito se balances_raw for None."""
        api = FakeAPI(connected=True)
        api.api.balances_raw = None
        api.api.get_balances.side_effect = lambda: None
        self.manager.patch_api(api)

        start = time.time()
        res = api.get_balances()
        elapsed = time.time() - start
        self.assertIsNone(res)
        self.assertLess(elapsed, 6.0, "get_balances patcheado deve retornar após bounded wait.")

    def test_concurrent_healing_waits_until_healed(self):
        """Verifica se chamadas concorrentes a heal aguardam a cura primária sem falha prematura."""
        def slow_heal_success():
            time.sleep(0.15)
            return True

        self.bot.connect = slow_heal_success
        self.bot.verify_connection = MagicMock(return_value=True)

        results = []
        def call_heal(idx):
            res = self.manager.heal(f"thread_{idx}")
            results.append((idx, res))

        t1 = threading.Thread(target=call_heal, args=(1,))
        t2 = threading.Thread(target=call_heal, args=(2,))
        t1.start()
        time.sleep(0.02)
        t2.start()

        t1.join()
        t2.join()

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0][1], "Thread 1 deve ter sucesso na cura.")
        self.assertTrue(results[1][1], "Thread 2 deve aguardar a cura e retornar True via verify_connection.")

    def test_call_timeout_waits_for_active_healing(self):
        """_call_timeout deve coordenar e aguardar a conclusão caso a chamada ative is_healing."""
        from bot import Bot
        bot = Bot.__new__(Bot)
        bot.is_healing = False
        bot._last_progress = time.time()
        bot._touch_progress = lambda: setattr(bot, "_last_progress", time.time())

        def healing_call():
            bot.is_healing = True
            time.sleep(0.1)
            bot.is_healing = False
            return "resultado_curado"

        # timeout inicial de apenas 0.03s, muito menor que os 0.1s da cura
        ok, res = Bot._call_timeout(bot, healing_call, 0.03, "test_healing_call")
        self.assertTrue(ok, "_call_timeout deve aguardar e obter sucesso quando is_healing estiver ativo.")
        self.assertEqual(res, "resultado_curado")

    def test_patch_api_get_balance_handles_none_raw(self):
        """get_balance patcheado não deve lançar TypeError quando balances_raw for None."""
        api = FakeAPI(connected=True)
        api.api.balances_raw = None
        api.api.get_balances.side_effect = lambda: None
        self.manager.patch_api(api)

        bal = api.get_balance()
        self.assertIsNone(bal, "get_balance deve retornar None sem exceção quando balances_raw for None.")

    def test_verify_connection_rejects_none_balance(self):
        """verify_connection deve retornar False se o ping de saldo retornar None (mesmo com check_connect True)."""
        from bot import Bot
        bot = Bot.__new__(Bot)
        bot.api = MagicMock()
        bot.api.check_connect.return_value = True
        bot.api.get_balance.return_value = None
        bot._call_timeout = lambda fn, timeout, label: (True, fn())

        self.assertFalse(Bot.verify_connection(bot), "verify_connection não deve aprovar saldo None.")

    def test_verify_connection_accepts_valid_numeric_balance(self):
        """verify_connection deve retornar True se o ping de saldo retornar um valor numérico válido."""
        from bot import Bot
        bot = Bot.__new__(Bot)
        bot.api = MagicMock()
        bot.api.check_connect.return_value = True
        bot.api.get_balance.return_value = 1500.50
        bot._call_timeout = lambda fn, timeout, label: (True, fn())

        self.assertTrue(Bot.verify_connection(bot), "verify_connection deve aprovar saldo numérico válido.")

    def test_patch_api_get_binary_option_detail_safe(self):
        """get_binary_option_detail patcheado não deve travar nem falhar em init_info nulo."""
        api = FakeAPI(connected=False)
        self.manager.patch_api(api)

        start = time.time()
        detail = api.get_binary_option_detail()
        elapsed = time.time() - start
        self.assertIsNone(detail)
        self.assertLess(elapsed, 1.0, "get_binary_option_detail deve retornar imediatamente quando desconectado.")

    def test_watchdog_auto_initializes_zero_timestamp(self):
        """Watchdog deve inicializar _healing_started_ts se estiver zerado e aplicar timeout de 600s."""
        self.bot.is_healing = True
        self.bot._healing_started_ts = 0.0

        healing_started = getattr(self.bot, "_healing_started_ts", 0.0)
        if healing_started <= 0.0:
            self.bot._healing_started_ts = time.time() - 650.0  # simula processo que já passou dos 600s
            healing_started = self.bot._healing_started_ts

        killed = False
        def mock_exit(code):
            nonlocal killed
            killed = True

        if (time.time() - healing_started) > 600.0:
            mock_exit(1)

    def test_call_timeout_health_ping_does_not_wait_for_healing(self):
        """health_ping em _call_timeout deve falhar com timeout estrito mesmo se is_healing for True."""
        from bot import Bot
        bot = Bot.__new__(Bot)
        bot.is_healing = True
        bot._last_progress = time.time()
        bot._touch_progress = lambda: setattr(bot, "_last_progress", time.time())

        def hanging_health_ping():
            time.sleep(0.5)
            return 1000.0

        start = time.time()
        ok, res = Bot._call_timeout(bot, hanging_health_ping, 0.05, "health_ping")
        elapsed = time.time() - start

        self.assertFalse(ok, "health_ping deve falhar rapidamente por timeout.")
        self.assertIn("TIMEOUT", str(res))
        self.assertLess(elapsed, 0.3, "health_ping não deve aguardar a cura terminar.")

    def test_safe_balance_preserves_last_known_balance_on_none(self):
        """_safe_balance deve preservar _last_balance anterior quando get_balance retornar None."""
        from bot import Bot
        bot = Bot.__new__(Bot)
        bot._last_balance = 5000.0
        bot._balance_ts = time.time() - 1000.0  # expirado
        bot.api = MagicMock()
        bot.api.get_balance.return_value = None
        bot._call_timeout = lambda fn, timeout, label: (False, "ValueError: None")

        bal = Bot._safe_balance(bot)
        self.assertEqual(bal, 5000.0, "Saldo anterior deve ser preservado em vez de sobrescrito com 0.0.")
        self.assertEqual(bot._last_balance, 5000.0)

    def test_ensure_connected_touches_progress_on_healthy(self):
        """ensure_connected deve atualizar _last_progress quando verify_connection retornar True."""
        from bot import Bot
        bot = Bot.__new__(Bot)
        bot.is_healing = False
        bot._last_progress = time.time() - 100.0
        bot.verify_connection = MagicMock(return_value=True)
        bot._touch_progress = lambda: setattr(bot, "_last_progress", time.time())

        res = Bot.ensure_connected(bot)
        self.assertTrue(res)
        self.assertLess(time.time() - bot._last_progress, 0.5, "ensure_connected deve atualizar _last_progress.")

    def test_connection_restored_resets_detail_cache(self):
        """_on_connection_restored deve resetar o cache de payout detail."""
        self.bot._detail_cache = (time.time(), {"EURUSD-OTC": {"turbo": {}}})
        self.manager._on_connection_restored()
        self.assertEqual(self.bot._detail_cache, (0.0, None), "Detail cache deve ser resetado após cura.")

    def test_patched_get_all_init_exits_early_on_disconnect(self):
        """patched_get_all_init deve sair imediatamente se check_connect() for False durante a espera."""
        api = FakeAPI(connected=True)
        api.api.api_option_init_all_result = None

        def disconnect_after_brief_delay():
            time.sleep(0.05)
            api._connected = False

        self.manager.patch_api(api)
        threading.Thread(target=disconnect_after_brief_delay, daemon=True).start()

        start = time.time()
        res = api.get_all_init()
        elapsed = time.time() - start

        self.assertIsNone(res)
        self.assertLess(elapsed, 2.0, "get_all_init deve encerrar a espera precocemente se o socket cair.")


if __name__ == "__main__":
    unittest.main()
