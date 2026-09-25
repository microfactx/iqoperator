"""
Semantic Context Pager.
Generates ultra-compact subgraphs and interface projections (k-hop neighborhood).
"""

from __future__ import annotations
from typing import Dict, Set, List
from .tsg_engine import TopologicalStateGraph, ASTNodeState


class SemanticContextPager:
    """
    Pagina o contexto de código em micro-projeções semânticas.
    Elimina o envio de arquivos inteiros enviando apenas o nó-alvo
    e os contratos de interface dos vizinhos topológicos de raio K.
    """

    def __init__(self, tsg: TopologicalStateGraph):
        self.tsg = tsg

    def page_neighborhood(self, target_node_id: str, k_hops: int = 1) -> str:
        """
        Gera uma página de contexto compacta para um nó específico.
        """
        target = self.tsg.get_node(target_node_id)
        if not target:
            return f"/* [NSAH_PAGER_ERROR]: Node '{target_node_id}' not found in TSG */"

        visited: Set[str] = {target_node_id}
        current_frontier: Set[str] = {target_node_id}

        for _ in range(k_hops):
            next_frontier: Set[str] = set()
            for nid in current_frontier:
                node = self.tsg.get_node(nid)
                if node:
                    for dep in node.dependencies | node.dependents:
                        if dep not in visited and dep in self.tsg.nodes:
                            visited.add(dep)
                            next_frontier.add(dep)
            current_frontier = next_frontier

        # Renderiza a projeção semântica compacta
        lines: List[str] = []
        lines.append(f"// === SEMANTIC PAGE: {target.node_id} ===")
        lines.append(f"// File: {target.file_path} (L{target.start_line}-L{target.end_line})")
        lines.append(f"// Target Contract: {target.signature}")
        if target.docstring:
            first_line_doc = target.docstring.strip().splitlines()[0]
            lines.append(f"// Doc: {first_line_doc[:80]}")
        lines.append("")

        # Vizinhos (Apenas contratos de interface de 1 linha compacta)
        neighbors = visited - {target_node_id}
        if neighbors:
            lines.append("// --- TOPOLOGICAL INTERFACE NEIGHBORS (Radius k=1) ---")
            for nid in sorted(list(neighbors))[:8]:  # Limita aos 8 vizinhos mais relevantes
                n = self.tsg.get_node(nid)
                if n:
                    rel = "USES" if nid in target.dependencies else "USED_BY"
                    sig = n.signature[:60]
                    lines.append(f"// [{rel}] {n.node_id} -> {sig}")
            lines.append("")

        return "\n".join(lines)

    def estimate_token_footprint(self, text: str) -> int:
        """Estimativa aproximada de tokens (1 token ~= 4 caracteres)."""
        return max(1, len(text) // 4)
