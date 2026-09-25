"""
Unit and Integration Tests for Synaptic Hypervisor (NSAH).
Validates token reduction, AST graph generation, Micro-DSL, and noise suppression.
"""

import sys
import unittest
from pathlib import Path

# Adiciona o diretório atual ao sys.path para importar synaptic_hypervisor
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from synaptic_hypervisor.core.tsg_engine import TopologicalStateGraph, ASTNodeState
from synaptic_hypervisor.core.context_pager import SemanticContextPager
from synaptic_hypervisor.core.micro_dsl import MicroDSLEngine, SymbolicInstruction
from synaptic_hypervisor.core.sandbox_runner import DeterministicSandbox
from synaptic_hypervisor.arbiter.invariant_judge import InvariantJudge
from synaptic_hypervisor.sidecar.daemon import SynapticHypervisorSidecar


class TestSynapticHypervisor(unittest.TestCase):

    def setUp(self):
        self.workspace_root = ROOT_DIR
        self.tsg = TopologicalStateGraph(self.workspace_root)
        self.tsg.index_codebase(max_files=30)
        self.pager = SemanticContextPager(self.tsg)
        self.sandbox = DeterministicSandbox(self.workspace_root)

    def test_tsg_indexing(self):
        """Verifica se o Grafo de Estado Topológico indexou nós com sucesso."""
        self.assertGreater(len(self.tsg.nodes), 0, "TSG deve conter nós indexados da base de código.")
        
        # Pega qualquer nó indexado para verificar o contrato de interface
        sample_node = next(iter(self.tsg.nodes.values()))
        self.assertIsInstance(sample_node, ASTNodeState)
        self.assertTrue(len(sample_node.signature) > 0)
        self.assertTrue(sample_node.start_line > 0)
        self.assertTrue(sample_node.end_line >= sample_node.start_line)

    def test_context_pager_k_hops(self):
        """Verifica se a projeção semântica é significativamente menor que o arquivo original."""
        sample_node_id = next(iter(self.tsg.nodes.keys()))
        page = self.pager.page_neighborhood(sample_node_id, k_hops=1)
        
        self.assertIn("SEMANTIC PAGE", page)
        self.assertIn(sample_node_id, page)
        
        tokens = self.pager.estimate_token_footprint(page)
        # Uma página semântica compacta com vizinhos deve ter menos de 300 tokens
        self.assertLess(tokens, 300, "A página semântica não deve exceder 300 tokens.")

    def test_micro_dsl_roundtrip_and_compression(self):
        """Verifica o parser e a taxa de compressão da Micro-DSL."""
        target = "kelly::calculate_kelly"
        delta = "+fractional_multiplier: float = 0.5; +kelly_val *= fractional_multiplier"
        invariant = "test_kelly_fractional PASS"

        raw_ir = MicroDSLEngine.emit_mutate(target, delta, invariant)
        parsed = MicroDSLEngine.parse(raw_ir)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.opcode, "MUTATE")
        self.assertEqual(parsed.target_node, target)
        self.assertEqual(parsed.payload, delta)
        self.assertEqual(parsed.invariant, invariant)

        # Simula a mensagem equivalente em linguagem natural prolixa
        nl_prompt = (
            "Olá caro assistente, precisamos que você abra o arquivo kelly.py e encontre a função "
            "calculate_kelly. Nela, gostaríamos que você adicionasse um parâmetro chamado "
            "fractional_multiplier com valor padrão de 0.5 e multiplicasse o valor calculado do "
            "kelly_val por essa fração. Além disso, certifique-se de validar se o teste "
            "test_kelly_fractional está passando sem quebrar as outras dependências."
        )

        savings = MicroDSLEngine.calculate_token_savings(nl_prompt, raw_ir)
        self.assertGreaterEqual(savings["reduction_percentage"], 60.0)

    def test_deterministic_sandbox_noise_filter(self):
        """Verifica se o Sandbox suprime ruído de terminal e extrai a essência do erro."""
        # Teste de validação sintática direta
        valid, msg = self.sandbox.check_python_syntax("def foo(): pass")
        self.assertTrue(valid)
        self.assertEqual(msg, "SYNTAX_OK")

        invalid, err_msg = self.sandbox.check_python_syntax("def foo( broken syntax")
        self.assertFalse(invalid)
        self.assertIn("ERR_SYNTAX", err_msg)

        # Teste de destilação de log ruidoso
        noisy_traceback = """
        Traceback (most recent call last):
          File "runner.py", line 420, in run_suite
          File "test_case.py", line 12, in test_something
          File "assertion_library.py", line 99, in assert_equal
        AssertionError: Expected 200 OK, got 500 Internal Server Error
        """
        distilled = self.sandbox._distill_error_output("", noisy_traceback)
        self.assertIn("ERR_ASSERTIONERROR", distilled)
        self.assertNotIn("runner.py", distilled)  # Garante que as linhas inúteis foram descartadas

    def test_invariant_arbiter_bundle(self):
        """Verifica se o pacote de prova para o modelo sênior é formal e compacto."""
        bundle = InvariantJudge.create_bundle(
            target_node="trade::execute_order",
            original_contract="def execute_order(qty: float) -> bool",
            mutated_contract="def execute_order(qty: float, stop_loss: float) -> bool",
            sandbox_verdict="EXEC_OK[Syntax + Invariants Passed]",
            symbolic_delta="MUTATE[trade::execute_order]{+stop_loss: float} CHECK{risk_check}"
        )
        prompt = bundle.to_arbiter_prompt()
        self.assertIn("FORMAL_INVARIANT_ARBITRATION_FRAME", prompt)
        tokens = len(prompt) // 4
        self.assertLess(tokens, 150, "O prompt de arbitragem deve consumir menos de 150 tokens.")

        # Teste do parser de decisão
        decision = InvariantJudge.parse_decision("DECISION: APPROVE")
        self.assertTrue(decision["approved"])

        rejection = InvariantJudge.parse_decision("DECISION: REJECT [Violates risk invariance]")
        self.assertFalse(rejection["approved"])

    def test_sidecar_benchmark_simulation(self):
        """Executa a simulação completa do Sidecar e valida redução > 80% de tokens."""
        sidecar = SynapticHypervisorSidecar(self.workspace_root)
        bench = sidecar.run_benchmark_simulation()
        
        self.assertIn("token_reduction_pct", bench)
        self.assertGreaterEqual(bench["token_reduction_pct"], 80.0)


if __name__ == "__main__":
    unittest.main()
