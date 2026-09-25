## 2026-09-24T23:47:28Z

<USER_REQUEST>
<original_task>
# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: small focused team

This is a single self-contained fix; keep it small and focused.

O bot sofre quedas constantes no deploy do Railway (reiniciado pelo Watchdog). Os logs revelam perda de conexão (`**error** get_candles need reconnect`, `TIMEOUT após 30s`) e congelamento no `get_betinfo`. Precisamos implementar uma "Homeostase Autonômica": um mecanismo resiliente de reconexão na biblioteca IQOption que recupere a sessão e evite que o Watchdog mate o processo durante quedas temporárias da corretora.

Working directory: c:/Users/WDAGUtilityAccount/Downloads/Nova pasta
Integrity mode: development

## Verification Resources (Logs de Erro)
```text
[err] ERROR **error** get_candles need reconnect
[err] WARNING get_candles AUDUSD-OTC: TIMEOUT após 30s em get_candles AUDUSD-OTC — pulando ciclo (1/3).
[err] ERROR **error** get_betinfo time out need reconnect
[err] ERROR WATCHDOG: sem progresso há 138s — reiniciando processo.
```

## Requirements

### R1. Mecanismo de Cura de Conexão (Reconnect Handling)
A equipe deve implementar um tratador de reconexão para lidar com os erros `need reconnect` do `get_candles` e `get_betinfo`. Quando a API da IQOption desconectar, o bot deve tentar um re-login/reconect suave com backoff exponencial, sem travar o thread principal infinitamente.

### R2. Sincronização com o Watchdog
A rotina de reconexão deve notificar o Watchdog interno de que o sistema está ativamente tentando se recuperar (estado de cura), impedindo que o Watchdog reinicie o processo abruptamente enquanto o bot aguarda o backoff da corretora.

### R3. Regras de Eficiência (Synaptic Orchestrator)
A equipe deve obrigatoriamente usar o ambiente de alta densidade semântica para todas as operações de leitura e testes:
- Não utilizar ferramentas padrão para ler arquivos inteiros.
- Utilizar a skill nativa detalhada em `synaptic_hypervisor/antigravity_integration/skills/synaptic-orchestrator/SKILL.md`.
- Executar testes e extrair código usando o daemon local (`python -m synaptic_hypervisor.sidecar.daemon`).

## Acceptance Criteria

### Homeostase de Conexão
- [ ] O sistema identifica falhas de socket/websocket da IQOption e aciona rotina de `reconnect()` ou `connect()`.
- [ ] O Watchdog não derruba a aplicação se ela estiver em loop controlado de reconexão (progress flag atualizada).
- [ ] O bot retoma o polling das 6 moedas assim que a conexão é restabelecida com sucesso.
</original_task>

<audit_target>
Working directory for your metadata and audit verdict: c:\Users\WDAGUtilityAccount\Downloads\Nova pasta\.agents\teamwork\auditor_1
Project root: c:\Users\WDAGUtilityAccount\Downloads\Nova pasta
Parent orchestrator conversation ID: c599c0b3-bf0c-4ddd-b666-6b348eb62935
Verification test suite: .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"

Conduct your independent 3-phase audit:
1. Timeline & commit audit
2. Cheating detection (ensure tests are genuine, no test modifications to mask failures, assertions test real logic)
3. Independent test execution & acceptance criteria verification (R1, R2, R3)

Deliver your structured audit verdict to handoff.md in your working directory and notify the parent via send_message.
</audit_target>
</USER_REQUEST>
