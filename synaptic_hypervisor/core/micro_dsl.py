"""
Symbolic Intermediate Representation (Micro-DSL).
High-density tokenless protocol for agent-to-agent communication.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class SymbolicInstruction:
    opcode: str               # "MUTATE", "QUERY", "PROVE", "ASSERT"
    target_node: str          # Identificador do nó alvo
    payload: str              # Delta de código ou predicado lógico
    invariant: Optional[str] = None  # Verificação formal esperada

    def to_ir(self) -> str:
        """Serializa para a sintaxe concisa da Micro-DSL."""
        check_part = f" CHECK{{{self.invariant}}}" if self.invariant else ""
        return f"{self.opcode}[{self.target_node}]{{{self.payload}}}{check_part}"


class MicroDSLEngine:
    """Parser e emissor da linguagem simbólica intermediária."""

    # Expressão regular para casar OPCODE[target]{payload} CHECK{invariant}
    PATTERN = re.compile(
        r"^(?P<opcode>[A-Z_]+)\[(?P<target>[^\]]+)\]\{(?P<payload>.*?)\}(?:\s*CHECK\{(?P<invariant>.*?)\})?$",
        re.DOTALL
    )

    @classmethod
    def parse(cls, raw_ir: str) -> Optional[SymbolicInstruction]:
        raw_ir = raw_ir.strip()
        match = cls.PATTERN.match(raw_ir)
        if not match:
            return None
        return SymbolicInstruction(
            opcode=match.group("opcode"),
            target_node=match.group("target"),
            payload=match.group("payload").strip(),
            invariant=match.group("invariant").strip() if match.group("invariant") else None
        )

    @classmethod
    def emit_mutate(cls, target_node: str, delta: str, invariant: str) -> str:
        inst = SymbolicInstruction(
            opcode="MUTATE",
            target_node=target_node,
            payload=delta.strip(),
            invariant=invariant.strip()
        )
        return inst.to_ir()

    @classmethod
    def emit_query(cls, target_pattern: str) -> str:
        inst = SymbolicInstruction(
            opcode="QUERY",
            target_node=target_pattern,
            payload=""
        )
        return inst.to_ir()

    @classmethod
    def calculate_token_savings(cls, natural_language: str, symbolic_ir: str) -> dict:
        """Compara o número aproximado de tokens e calcula a taxa de compressão."""
        nl_tokens = max(1, len(natural_language) // 4)
        ir_tokens = max(1, len(symbolic_ir) // 4)
        reduction_pct = max(0.0, ((nl_tokens - ir_tokens) / nl_tokens) * 100)
        return {
            "natural_language_tokens": nl_tokens,
            "symbolic_ir_tokens": ir_tokens,
            "reduction_percentage": round(reduction_pct, 2)
        }
