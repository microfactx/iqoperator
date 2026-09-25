# Token Firewall Rules for Subagents

Estas regras atuam como um firewall ativo para prevenir o esgotamento de cotas de tokens durante tarefas autônomas:

1. **PROIBIDO Despejo de Arquivos Inteiros**: Se um arquivo tiver mais de 50 linhas, use sempre intervalos estritos (`StartLine` e `EndLine`) ou consulte o Grafo de Estado Topológico.
2. **PROIBIDO Chat de Cortesia entre Agentes**: Subagentes devem responder em tuplas estruturadas, diffs atômicos ou instruções da Micro-DSL.
3. **SUPRESSÃO DE LOGS DE TERMINAL**: Nunca injete saídas de build de mais de 10 linhas no contexto de um LLM. Utilize o `DeterministicSandbox` para resumir a falha em tuplas diagnósticas (`ERR_*`).
4. **ARBITRAGEM CIRÚRGICA**: Decisões de arquitetura devem ser tomadas com base em provas de invariantes compactas (< 300 tokens), evitando reprocessamento de todo o histórico do chat.
