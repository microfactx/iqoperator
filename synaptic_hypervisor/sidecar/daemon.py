"""
Synaptic Hypervisor Sidecar Daemon & CLI.
Provides local services for semantic context paging, Micro-DSL compilation,
and deterministic speculative sandbox execution.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from ..core.tsg_engine import TopologicalStateGraph
from ..core.context_pager import SemanticContextPager
from ..core.micro_dsl import MicroDSLEngine
from ..core.sandbox_runner import DeterministicSandbox
from ..arbiter.invariant_judge import InvariantJudge


class SynapticHypervisorSidecar:
    """Núcleo integrado do Hypervisor executável como serviço ou CLI."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path)
        self.tsg = TopologicalStateGraph(self.workspace_path)
        self.pager = SemanticContextPager(self.tsg)
        self.sandbox = DeterministicSandbox(self.workspace_path)

    def initialize_graph(self):
        self.tsg.index_codebase()

    def get_semantic_page(self, node_id: str, k_hops: int = 1) -> str:
        return self.pager.page_neighborhood(node_id, k_hops=k_hops)

    def run_benchmark_simulation(self) -> dict:
        """
        Simula a diferença de tokens entre o fluxo tradicional (/boost ou /teamwork-preview)
        e o fluxo otimizado com o Synaptic Hypervisor.
        """
        # Exemplo realista de cenário de refatoração em sistema de trading
        traditional_prompt = (
            "Você é o agente DeepCoder. Por favor analise os arquivos config.py e kelly.py. "
            "Veja abaixo o conteúdo de config.py (150 linhas), seguido pelo conteúdo de kelly.py (80 linhas). "
            "Precisamos alterar o cálculo de Kelly Criterion para suportar fractional kelly e stop loss. "
            "Aqui está o traceback completo dos testes anteriores que falharam com 300 linhas de logs de traceback do terminal... "
            "[Traceback repetido 3 vezes nas iterações anteriores de revisão do /boost] "
            "Escreva os arquivos novamente por completo com as alterações."
        )

        # Micro-DSL e Projeção Semântica do Synaptic Hypervisor
        target_node = "kelly::calculate_kelly"
        self.initialize_graph()
        semantic_page = self.get_semantic_page(target_node, k_hops=1)
        
        ir_instruction = MicroDSLEngine.emit_mutate(
            target_node=target_node,
            delta="+fractional_multiplier: float = 0.5; +kelly_val *= fractional_multiplier",
            invariant="test_kelly_fractional PASS and kelly_val > 0"
        )

        proof_bundle = InvariantJudge.create_bundle(
            target_node=target_node,
            original_contract="def calculate_kelly(win_rate: float, win_loss_ratio: float) -> float",
            mutated_contract="def calculate_kelly(win_rate: float, win_loss_ratio: float, frac: float = 0.5) -> float",
            sandbox_verdict="EXEC_OK[Syntax + 4 tests passed]",
            symbolic_delta=ir_instruction
        )
        arbiter_frame = proof_bundle.to_arbiter_prompt()

        # Tokens Tradicionais vs Tokens Hypervisor
        # Tradicional: leitura de arquivos completos + chat prolixo + logs repetidos a cada round
        trad_tokens = (len(traditional_prompt) // 4) + 3500  # ~4.000 tokens por round, múltiplos rounds = 16k+
        hyp_tokens = (len(semantic_page) // 4) + (len(ir_instruction) // 4) + (len(arbiter_frame) // 4)

        savings = MicroDSLEngine.calculate_token_savings(
            natural_language=traditional_prompt + ("X" * 12000),  # simulando 3 rounds acumulados
            symbolic_ir=semantic_page + "\n" + ir_instruction + "\n" + arbiter_frame
        )

        return {
            "scenario": "Refatoração de Kelly Criterion e Configuração",
            "traditional_estimated_tokens": savings["natural_language_tokens"],
            "synaptic_hypervisor_tokens": savings["symbolic_ir_tokens"],
            "token_reduction_pct": savings["reduction_percentage"],
            "ir_instruction_sample": ir_instruction,
            "arbiter_frame_sample": arbiter_frame
        }


def main():
    parser = argparse.ArgumentParser(description="Synaptic Hypervisor Sidecar CLI")
    parser.add_argument("command", choices=["benchmark", "index", "page", "dsl"], help="Comando a executar")
    parser.add_argument("--node", help="ID do nó para paginação")
    parser.add_argument("--workspace", default=".", help="Raiz do workspace")

    args = parser.parse_args()
    sidecar = SynapticHypervisorSidecar(args.workspace)

    if args.command == "benchmark":
        results = sidecar.run_benchmark_simulation()
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.command == "index":
        sidecar.initialize_graph()
        print(f"TSG indexado com sucesso! Total de nós mapeados: {len(sidecar.tsg.nodes)}")
    elif args.command == "page":
        if not args.node:
            print("Erro: especifique --node para paginar.")
            sys.exit(1)
        sidecar.initialize_graph()
        page = sidecar.get_semantic_page(args.node)
        print(page)
    elif args.command == "dsl":
        sample = MicroDSLEngine.emit_mutate("auth::login", "+validate_mfa()", "mfa_verified == True")
        print("Amostra de Micro-DSL emitido:")
        print(sample)


if __name__ == "__main__":
    main()
