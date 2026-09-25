"""
Formal Invariant Arbiter.
Prepares ultra-compact formal verification bundles for senior reasoning models.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class InvariantProofBundle:
    target_node: str
    original_contract: str
    mutated_contract: str
    sandbox_verdict: str
    symbolic_delta: str

    def to_arbiter_prompt(self) -> str:
        """
        Renderiza um prompt de arbitragem estritamente formal.
        Consumo médio: < 250 tokens (em vez de 100k+ de chat e arquivos).
        """
        return f"""[FORMAL_INVARIANT_ARBITRATION_FRAME]
TARGET: {self.target_node}
PRE_CONTRACT: {self.original_contract}
POST_CONTRACT: {self.mutated_contract}
DELTA: {self.symbolic_delta}
LOCAL_PROOF_VERDICT: {self.sandbox_verdict}

CRITERIA: Verify if mutated contract satisfies system invariants without breaking dependencies.
REPLY STRICTLY: 'DECISION: APPROVE' or 'DECISION: REJECT [Reason in < 15 words]'
[/FORMAL_INVARIANT_ARBITRATION_FRAME]"""


class InvariantJudge:
    """Validador formal que coordena a emissão do pacote de arbitragem."""

    @classmethod
    def create_bundle(
        cls,
        target_node: str,
        original_contract: str,
        mutated_contract: str,
        sandbox_verdict: str,
        symbolic_delta: str
    ) -> InvariantProofBundle:
        return InvariantProofBundle(
            target_node=target_node,
            original_contract=original_contract,
            mutated_contract=mutated_contract,
            sandbox_verdict=sandbox_verdict,
            symbolic_delta=symbolic_delta
        )

    @classmethod
    def parse_decision(cls, raw_decision: str) -> dict:
        raw = raw_decision.strip()
        is_approved = "APPROVE" in raw.upper() and "REJECT" not in raw.upper()
        return {
            "approved": is_approved,
            "raw": raw
        }
