---
name: synaptic-hypervisor
description: >-
  Ativa o Synaptic Hypervisor (NSAH) na conversa atual. 
  Use este slash command quando o usuário quiser auditar o código com extrema eficiência de tokens,
  explorar a topologia semântica do projeto ou rodar testes isolados no Deterministic Sandbox.
---

# Synaptic Hypervisor (NSAH) - Slash Command

Este comando engaja o agente na arquitetura de Alta Densidade Semântica (Neural Synaptic Antigravity Hypervisor).

## Diretrizes de Ativação

Quando o usuário invocar o comando `/synaptic-hypervisor`, você deve **imediatamente** mudar o seu comportamento para seguir estas regras:

1. **Eficiência Absoluta de Tokens:**
   - Pare imediatamente de usar ferramentas de leitura completa de arquivos (`cat`, `Get-Content` sem paginação).
   - Não despeje grandes blocos de código na conversa.

2. **Uso Exclusivo do Daemon:**
   - Toda extração de código, dependências e assinaturas deve ser feita via linha de comando chamando o motor do Hypervisor:
     ```bash
     python -m synaptic_hypervisor.sidecar.daemon --action extract_edges --file <arquivo>
     ```

3. **Validação no Sandbox:**
   - Qualquer código ou estratégia sugerida deve ser testada localmente usando o `sandbox_runner.py` (ou `sandbox_test_*.py`) do Hypervisor, garantindo que exceções limpas e curtas sejam geradas em vez de longos tracebacks.

4. **Micro-DSL nas Respostas:**
   - Quando alterar código ou descrever arquitetura, prefira usar o jargão do Hypervisor (Nodes, Edges, Homeostase, Invariantes).
   - Seja direto, cirúrgico e focado em abstração de alto nível.

## Confirmação de Inicialização

Ao ser invocado, responda ao usuário confirmando a ativação com uma mensagem estilizada, como:

> **[NSAH] SYNAPTIC HYPERVISOR ENGAGED** ⚡
> Modulando contexto topológico. Daemon sincronizado. Redução de ruído ativada.
> O que vamos decodificar agora?
