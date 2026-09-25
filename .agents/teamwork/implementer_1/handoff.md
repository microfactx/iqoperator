# Handoff Report — Homeostase Autonômica de Conexão e Sincronização de Watchdog

## 1. O que foi alterado
- `homeostasis.py`: Novo módulo centralizador de resiliência e recuperação autonômica da conexão com a IQOption.
  - Implementou `HomeostasisManager` com backoff exponencial configurável (2s, 4s, 8s... até 60s) e heartbeat contínuo para o Watchdog (`sleep_with_heartbeat`).
  - Implementou flag `is_healing` para coordenar o estado de cura.
  - Implementou wrappers resilientes `resilient_get_candles` e `resilient_get_betinfo` que eliminam os loops infinitos (`while True:` e busy-wait de 100% de CPU com `self.check_connect`), interceptam exceções de rede/socket (`need reconnect`), e acionam a rotina de cura de forma limpa.
  - Implementou método `_on_connection_restored` que zera `_candle_fail`, redefine `_asset_cursor = 0` e reseta contadores de falhas globais.
- `bot.py`:
  - Integrado `HomeostasisManager` no `Bot.__init__`.
  - Atualizado `_start_watchdog`: agora verifica `self.is_healing` antes de verificar o timeout inativo; durante a recuperação, atualiza a flag de progresso (`_touch_progress()`) e não derruba o processo.
  - Substituído `time.sleep` estático por `sleep_with_heartbeat` no lock de conexão (`_locked_connect`), no loop de reconexão `connect()` e no ciclo principal `run()`.
  - Atualizado `ensure_connected`: usa `verify_connection()` (ping real via `get_balance()`) e delega a reconexão para `self.homeostasis.heal()`, removendo o `os._exit(1)` prematuro após 2 tentativas.
  - Atualizado `candles_df` e `_poll_pending`: se ocorrer erro contendo `need reconnect` ou timeout, a homeostase é disparada imediatamente.
  - Atualizado o disjuntor de outage global em `run()`: tenta recuperação homeostática antes de forçar o reinício do processo.
- `config.py`:
  - Definido `DEFAULT_ASSETS = ["EURUSD-OTC", "GBPUSD-OTC", "USDJPY-OTC", "AUDUSD-OTC", "EURGBP-OTC", "USDCAD-OTC"]` como fallback padrão de 6 moedas se `IQ_ASSETS`/`IQ_ASSET` não estiverem setados.
- `tests/test_homeostasis.py`:
  - 15 novos testes unitários e de integração cobrindo:
    - Recuperação com backoff exponencial e heartbeat.
    - Sincronização do Watchdog (tolerância no estado `is_healing`).
    - Wrappers resilientes de `get_candles` e `get_betinfo` em casos de sucesso, desconexão, exceção de socket e timeout.
    - Proteção contra requisições concorrentes de reconexão.
    - Retomada imediata do polling das 6 moedas após reconexão.

## 2. Por que foi alterado
- O bot sofria quedas constantes no deploy do Railway reiniciado pelo Watchdog interno devido a interrupções temporárias de websocket da IQOption (`**error** get_candles need reconnect`, `TIMEOUT após 30s` e `**error** get_betinfo time out need reconnect`).
- Na biblioteca `iqoptionapi`, `get_candles` e `get_betinfo` possuíam loops infinitos `while True:` com busy-wait de 100% de CPU que nunca retornavam caso o websocket caísse, causando estouro do timeout de 30s do `_call_timeout` e abandono de threads zumbis.
- Durante tentativas de reconexão, `bot.py` realizava `time.sleep(30 * attempt)` sem atualizar `_last_progress`, fazendo com que o Watchdog (timeout de 120s) derrubasse o processo em ~138s.
- A homeostase implementada protege o ciclo de vida da aplicação com cura suave, backoff exponencial e comunicação contínua com o Watchdog.

## 3. Registro de Verificação
- **Deep Verification (testes reais executados):**
  - Executados 21 testes unitários (`python -m unittest discover -s tests -p "test_*.py"`): 100% aprovados em 3.968s.
  - Executados 6 testes de integração do Hypervisor (`tests/test_synaptic_hypervisor.py`): 100% aprovados.
  - Executado teste determinístico em sandbox (`DeterministicSandbox.run_isolated_command`): retorno `EXEC_OK[Code 0]`.
  - Validação de sintaxe via AST (`DeterministicSandbox.check_python_syntax`): `SYNTAX_OK` para `homeostasis.py` e `bot.py`.
  - Indexação topológica TSG (`synaptic_hypervisor.sidecar.daemon index`): 224 nós indexados com mapeamento completo de dependências.
- **Shallow Verification (inspeção manual):**
  - Revisão minuciosa do diff em `bot.py` e `config.py`.
- **Aspectos não verificados:**
  - Conexão em tempo real com credenciais ativas da IQOption em ambiente de produção (necessita credenciais reais do usuário no Railway).
