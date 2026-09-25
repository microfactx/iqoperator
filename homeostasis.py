"""
Homeostase Autonômica — Módulo de Resiliência de Conexão e Sincronização com o Watchdog.

Implementa:
1. Mecanismo de Cura de Conexão com backoff exponencial.
2. Sincronização contínua com o Watchdog (evita morte por timeout durante recuperação).
3. Wrappers resilientes para get_candles, get_betinfo e get_balances contra falhas de socket/websocket.
4. Recuperação imediata de ativos (6 moedas) após reconexão bem-sucedida.
"""

from __future__ import annotations
import logging
import threading
import time
from typing import Any

log = logging.getLogger("iqrobot")


class HomeostasisManager:
    """Controlador central de homeostase e cura de conexão."""

    def __init__(
        self,
        bot: Any,
        initial_backoff: float = 2.0,
        backoff_factor: float = 2.0,
        max_backoff: float = 60.0,
        max_attempts: int = 10,
    ):
        self.bot = bot
        self.initial_backoff = initial_backoff
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.max_attempts = max_attempts
        self._lock = threading.Lock()
        self.is_healing = False
        self._healing_event = threading.Event()
        self._healing_event.set()

    def heal(self, reason: str = "") -> bool:
        """
        Executa a rotina de reconexão suave com backoff exponencial.
        Sincroniza o Watchdog interno para que ele saiba que o sistema está em 'estado de cura'.
        """
        with self._lock:
            if self.is_healing:
                already_healing = True
            else:
                self.is_healing = True
                if hasattr(self.bot, "is_healing"):
                    self.bot.is_healing = True
                if hasattr(self.bot, "_healing_started_ts"):
                    self.bot._healing_started_ts = time.time()
                self._healing_event.clear()
                already_healing = False

        if already_healing:
            log.info(f"HOMEOSTASE: Cura já em andamento. Aguardando conclusão (motivo concorrente: {reason}).")
            start_wait = time.time()
            while time.time() - start_wait < 600.0:
                if self._healing_event.wait(timeout=1.0):
                    break
                self._touch_bot_progress()
            return self.bot.verify_connection()

        self._touch_bot_progress()
        log.warning(f"HOMEOSTASE: [ESTADO DE CURA ATIVADO] Motivo: {reason}")

        success = False
        try:
            for attempt in range(1, self.max_attempts + 1):
                self._touch_bot_progress()
                log.info(f"HOMEOSTASE: Tentativa de cura #{attempt}/{self.max_attempts}...")

                # Tenta reconectar
                try:
                    if attempt == 1:
                        connected = self.bot.connect()
                    else:
                        connected = self.bot._hard_reconnect()
                except Exception as e:
                    log.warning(f"HOMEOSTASE: Exceção na tentativa #{attempt}: {e}")
                    connected = False

                if connected:
                    # Validação via ping de saldo/conexão
                    if self.bot.verify_connection():
                        log.info("HOMEOSTASE: Conexão restabelecida com sucesso!")
                        self._on_connection_restored()
                        success = True
                        break
                    else:
                        log.warning("HOMEOSTASE: connect()=True mas validação de conexão falhou.")

                # Backoff exponencial com heartbeat para o Watchdog
                backoff = min(
                    self.initial_backoff * (self.backoff_factor ** (attempt - 1)),
                    self.max_backoff,
                )
                log.warning(
                    f"HOMEOSTASE: Tentativa #{attempt} falhou. "
                    f"Aguardando {backoff:.1f}s (backoff exponencial com heartbeat)..."
                )
                self.sleep_with_heartbeat(backoff)

        finally:
            with self._lock:
                self.is_healing = False
                if hasattr(self.bot, "is_healing"):
                    self.bot.is_healing = False
                if hasattr(self.bot, "_healing_started_ts"):
                    self.bot._healing_started_ts = 0.0
                self._healing_event.set()
            self._touch_bot_progress()

        if not success:
            log.error("HOMEOSTASE: Não foi possível restabelecer a conexão após as tentativas.")
        return success

    def _touch_bot_progress(self):
        """Atualiza a flag de progresso do bot para sincronização com o Watchdog."""
        if hasattr(self.bot, "_touch_progress"):
            try:
                self.bot._touch_progress()
            except Exception:
                pass

    def sleep_with_heartbeat(self, duration: float, chunk: float = 1.0):
        """
        Dorme pelo período duration em fatias pequenas, notificando o Watchdog a cada fração
        de tempo para que o processo nunca seja morto por inatividade durante a espera.
        """
        end_time = time.time() + duration
        while time.time() < end_time:
            self._touch_bot_progress()
            remaining = end_time - time.time()
            sleep_time = min(chunk, max(0.0, remaining))
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _on_connection_restored(self):
        """Restaura o estado de polling imediato das moedas após a cura."""
        if hasattr(self.bot, "_candle_fail"):
            self.bot._candle_fail.clear()
        if hasattr(self.bot, "_asset_cursor"):
            self.bot._asset_cursor = 0
        if hasattr(self.bot, "_consecutive_global_fails"):
            self.bot._consecutive_global_fails = 0
        if hasattr(self.bot, "_empty_scans"):
            self.bot._empty_scans = 0
        if hasattr(self.bot, "_quiet_until"):
            self.bot._quiet_until = 0.0
        if hasattr(self.bot, "_hard_reconnect_count"):
            self.bot._hard_reconnect_count = 0
        if hasattr(self.bot, "_last_balance"):
            self.bot._last_balance = None
        if hasattr(self.bot, "_balance_ts"):
            self.bot._balance_ts = 0.0
        if hasattr(self.bot, "_detail_cache"):
            self.bot._detail_cache = (0.0, None)
        self._touch_bot_progress()
        log.info("HOMEOSTASE: Cooldowns e contadores resetados. Polling de moedas retomado com sucesso.")

    def patch_api(self, api_instance: Any):
        """Instala os métodos de captura e reconexão resilientes na instância da IQ_Option."""
        if api_instance is None:
            return

        manager = self

        def patched_get_candles(actives, interval, count, endtime, timeout=10.0):
            return manager.get_candles(api_instance, actives, interval, count, endtime, timeout=timeout)

        def patched_get_betinfo(id_number, timeout=10.0):
            return manager.get_betinfo(api_instance, id_number, timeout=timeout)

        def patched_get_balances():
            if hasattr(api_instance, "api"):
                api_instance.api.balances_raw = None
                if hasattr(api_instance.api, "get_balances"):
                    try:
                        api_instance.api.get_balances()
                    except Exception:
                        pass
                start = time.time()
                while getattr(api_instance.api, "balances_raw", None) is None:
                    if time.time() - start > 5.0:
                        break
                    time.sleep(0.05)
                return getattr(api_instance.api, "balances_raw", None)
            return None

        api_instance.get_candles = patched_get_candles
        api_instance.get_betinfo = patched_get_betinfo
        api_instance.get_balances = patched_get_balances

        orig_get_balance = getattr(api_instance, "get_balance", None)

        def patched_get_balance():
            if hasattr(api_instance, "api") and hasattr(api_instance.api, "get_balances"):
                try:
                    balances_raw = patched_get_balances()
                    if not balances_raw or not isinstance(balances_raw, dict):
                        return None
                    msg = balances_raw.get("msg")
                    if not isinstance(msg, list):
                        return None
                    import iqoptionapi.global_value as global_value
                    for balance in msg:
                        if isinstance(balance, dict) and balance.get("id") == global_value.balance_id:
                            return balance.get("amount")
                    if msg and isinstance(msg[0], dict):
                        return msg[0].get("amount")
                except Exception as e:
                    log.warning(f"get_balance falhou: {e}")
                return None
            if orig_get_balance is not None:
                try:
                    return orig_get_balance()
                except Exception as e:
                    log.warning(f"orig_get_balance falhou: {e}")
                    return None
            return None

        def patched_get_all_init():
            if hasattr(api_instance, "check_connect") and not api_instance.check_connect():
                return None
            if not hasattr(api_instance, "api"):
                return None
            api_instance.api.api_option_init_all_result = None
            try:
                if hasattr(api_instance.api, "get_api_option_init_all"):
                    api_instance.api.get_api_option_init_all()
            except Exception:
                return None
            start = time.time()
            while getattr(api_instance.api, "api_option_init_all_result", None) is None:
                if hasattr(api_instance, "check_connect") and not api_instance.check_connect():
                    break
                if time.time() - start > 15.0:
                    break
                time.sleep(0.05)
            res = getattr(api_instance.api, "api_option_init_all_result", None)
            if isinstance(res, dict) and res.get("isSuccessful") is True:
                return res
            return None

        def patched_get_binary_option_detail():
            init_info = patched_get_all_init()
            if not init_info or not isinstance(init_info, dict) or "result" not in init_info:
                return None
            try:
                from collections import defaultdict
                detail = defaultdict(dict)
                result = init_info["result"]
                for mode in ("turbo", "binary"):
                    mode_actives = result.get(mode, {}).get("actives", {})
                    if isinstance(mode_actives, dict):
                        for act_id, act_data in mode_actives.items():
                            if isinstance(act_data, dict):
                                name = act_data.get("name", "")
                                if "." in name:
                                    name = name[name.index(".") + 1:]
                                if name:
                                    detail[name][mode] = act_data
                return dict(detail)
            except Exception as e:
                log.warning(f"get_binary_option_detail falhou: {e}")
                return None

        api_instance.get_balance = patched_get_balance
        api_instance.get_all_init = patched_get_all_init
        api_instance.get_binary_option_detail = patched_get_binary_option_detail
        api_instance._homeostasis = manager
        log.info("HOMEOSTASE: Wrappers resilientes instalados (get_candles, get_betinfo, get_balances, get_balance, get_binary_option_detail).")

    def get_candles(self, api_instance: Any, actives: str, interval: int, count: int, endtime: float, timeout: float = 10.0) -> list | None:
        """
        Wrapper resiliente para get_candles:
        - Bounded wait com time.sleep(0.05) em vez de 100% CPU spinning.
        - Identifica necessidade de reconexão e aciona heal().
        - Não congela a thread com loop infinito (while True).
        - Trata ativos não mapeados sem disparar falso reconnect.
        """
        # Checagem de conexão prévia
        try:
            if hasattr(api_instance, "check_connect") and not api_instance.check_connect():
                log.warning(f"get_candles {actives}: check_connect() é False — disparando homeostase.")
                self.heal(reason=f"get_candles {actives}: websocket desconectado")
                return None
        except Exception:
            pass

        # Converte nome do ativo usando tabela interna se disponível
        active_id = None
        try:
            import iqoptionapi.constants as OP_code
            if actives in OP_code.ACTIVES:
                active_id = OP_code.ACTIVES[actives]
            else:
                try:
                    active_id = int(actives)
                except ValueError:
                    # Ativo desconhecido — tenta atualizar os opcodes se o método existir
                    if hasattr(api_instance, "update_ACTIVES_OPCODE"):
                        try:
                            api_instance.update_ACTIVES_OPCODE()
                        except Exception:
                            pass
                    if actives in OP_code.ACTIVES:
                        active_id = OP_code.ACTIVES[actives]
        except Exception:
            pass

        if active_id is None:
            # Ativo não reconhecido nos opcodes da corretora — ignora sem falso reconnect
            log.warning(f"get_candles {actives}: ativo não reconhecido em OP_code.ACTIVES — pulando.")
            return None

        # Prepara buffer
        try:
            if hasattr(api_instance, "api") and hasattr(api_instance.api, "candles"):
                api_instance.api.candles.candles_data = None
        except Exception:
            pass

        # Executa getcandles no websocket interno
        try:
            if hasattr(api_instance, "api") and hasattr(api_instance.api, "getcandles"):
                api_instance.api.getcandles(active_id, interval, count, endtime)
            else:
                log.error("**error** get_candles need reconnect (api.getcandles indisponível)")
                self.heal(reason="getcandles indisponível")
                return None
        except Exception as e:
            if isinstance(e, (ValueError, TypeError, KeyError)):
                log.warning(f"get_candles {actives}: parâmetro inválido ({e}) — ignorando sem reconnect.")
                return None
            log.error(f"**error** get_candles need reconnect: {e}")
            self.heal(reason=f"get_candles {actives} exceção: {e}")
            return None

        # Espera com prazo determinado e verificação de integridade do socket
        start_wait = time.time()
        deadline = start_wait + timeout
        while time.time() < deadline:
            self._touch_bot_progress()
            try:
                if hasattr(api_instance, "check_connect") and not api_instance.check_connect():
                    log.error("**error** get_candles need reconnect (websocket desconectou durante espera)")
                    self.heal(reason=f"get_candles {actives} websocket caiu")
                    return None
            except Exception:
                pass

            try:
                data = getattr(api_instance.api.candles, "candles_data", None)
                if data is not None:
                    return data
            except Exception:
                pass
            time.sleep(0.05)

        log.error(f"**error** get_candles need reconnect (timeout após {timeout:.0f}s aguardando candles de {actives})")
        self.heal(reason=f"get_candles {actives} timeout {timeout:.0f}s")
        return None

    def get_betinfo(self, api_instance: Any, id_number: int, timeout: float = 10.0) -> tuple[bool, dict | None]:
        """
        Wrapper resiliente para get_betinfo:
        - Bounded wait (timeout de 10s padrão) com time.sleep(0.05).
        - Identifica timeout/queda de socket e aciona heal().
        - Retorna (False, None) em caso de erro, sem travar em while True infinito.
        """
        try:
            if hasattr(api_instance, "check_connect") and not api_instance.check_connect():
                log.warning(f"get_betinfo id={id_number}: check_connect() é False — disparando homeostase.")
                self.heal(reason=f"get_betinfo id={id_number}: websocket desconectado")
                return False, None
        except Exception:
            pass

        try:
            if hasattr(api_instance, "api") and hasattr(api_instance.api, "game_betinfo"):
                api_instance.api.game_betinfo.isSuccessful = None
        except Exception:
            pass

        try:
            if hasattr(api_instance, "api") and hasattr(api_instance.api, "get_betinfo"):
                api_instance.api.get_betinfo(id_number)
            else:
                log.error("**error** def get_betinfo self.api.get_betinfo reconnect (método indisponível)")
                self.heal(reason="get_betinfo indisponível")
                return False, None
        except Exception as e:
            if isinstance(e, (ValueError, TypeError)):
                log.warning(f"get_betinfo id={id_number}: parâmetro inválido ({e}) — ignorando.")
                return False, None
            log.error(f"**error** def get_betinfo self.api.get_betinfo reconnect: {e}")
            self.heal(reason=f"get_betinfo id={id_number} exceção: {e}")
            return False, None

        start_wait = time.time()
        deadline = start_wait + timeout
        while time.time() < deadline:
            self._touch_bot_progress()
            try:
                if hasattr(api_instance, "check_connect") and not api_instance.check_connect():
                    log.error("**error** get_betinfo time out need reconnect (websocket desconectou)")
                    self.heal(reason=f"get_betinfo id={id_number} websocket caiu")
                    return False, None
            except Exception:
                pass

            try:
                is_success = getattr(api_instance.api.game_betinfo, "isSuccessful", None)
                if is_success is not None:
                    if is_success is True:
                        return True, getattr(api_instance.api.game_betinfo, "dict", None)
                    return False, None
            except Exception:
                pass
            time.sleep(0.05)

        log.error("**error** get_betinfo time out need reconnect")
        self.heal(reason=f"get_betinfo id={id_number} timeout {timeout:.0f}s")
        return False, None
