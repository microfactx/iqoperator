---
name: synaptic-orchestrator
description: Aciona o Synaptic Hypervisor (NSAH) para orquestrações ultra-otimizadas com até 95% de economia de tokens sobre /boost e /teamwork-preview.
---

# Synaptic Orchestrator Skill

Esta skill habilita o agente a utilizar o **Synaptic Hypervisor (NSAH)** para resolver problemas complexos com pegada de tokens quase-zero.

## Quando Utilizar
- Tarefas de refatoração, debugging e desenvolvimento que exigiriam rodadas exaustivas de `/boost` ou equipes do `/teamwork-preview`.
- Quando a cota de tokens estiver baixa ou quando a eficiência de custo for crítica.

## Protocolo Operacional

1. **Paginação Semântica de Contexto (Context Paging):**
   - Nunca use `view_file` para despejar centenas de linhas de arquivos inteiros no chat.
   - Utilize a projeção de vizinhança topológica ($k=1$) via `TopologicalStateGraph` do Hypervisor para enviar apenas a assinatura e contratos das funções dependentes.

2. **Comunicação por Micro-DSL:**
   - Para delegar tarefas a subagentes executores, envie comandos na sintaxe simbólica:
     ```
     MUTATE[modulo::funcao]{delta de codigo} CHECK{invariante de teste}
     ```
   - Elimine conversas prolixas ou explicações pedagógicas entre agentes internos.

3. **Sandbox Determinística Local (Zero-Token Feedback Loop):**
   - Execute os testes e compilações localmente sem vazar logs longos de terminal para o LLM.
   - Trate falhas apenas com tuplas de erro discretas (`ERR_ASSERTION`, `ERR_SYNTAX`).

4. **Arbitragem por Invariantes (Reasoning Model):**
   - O modelo de raciocínio avançado apenas analisa o bundle final de prova formal (`InvariantProofBundle`), consumindo menos de 250 tokens por aprovação.
