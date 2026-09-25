"""
Topological State Graph (TSG) Engine.
Parses source code into an in-memory dependency & AST graph.
"""

from __future__ import annotations
import ast
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional


@dataclass
class ASTNodeState:
    node_id: str                      # ex: "module.submodule::ClassName.method_name"
    node_type: str                    # "function", "class", "method", "variable"
    file_path: str                    # Caminho relativo do arquivo
    start_line: int
    end_line: int
    signature: str                    # Assinatura (ex: "(self, token: str) -> bool")
    docstring: Optional[str] = None
    body_hash: str = ""               # SHA256 do corpo do nó
    interface_contract: str = ""      # Assinatura compactada com doc/tipos
    dependencies: Set[str] = field(default_factory=set)  # Símbolos que este nó chama/usa
    dependents: Set[str] = field(default_factory=set)    # Símbolos que usam este nó

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "signature": self.signature,
            "interface_contract": self.interface_contract,
            "body_hash": self.body_hash,
            "dependencies": sorted(list(self.dependencies)),
            "dependents": sorted(list(self.dependents)),
        }


class CodebaseASTVisitor(ast.NodeVisitor):
    """Extrai definições e relações de chamadas de um módulo Python."""

    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.module_prefix = Path(file_path).with_suffix("").as_posix().replace("/", ".")
        self.current_scope: List[str] = [self.module_prefix]
        self.nodes: Dict[str, ASTNodeState] = {}
        self.calls_in_node: Dict[str, Set[str]] = {}

    def _get_node_source(self, node: ast.AST) -> str:
        if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
            sl = node.lineno - 1
            el = node.end_lineno
            return "\n".join(self.lines[sl:el])
        return ""

    def _hash_content(self, text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]

    def _format_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        args = []
        for arg in node.args.args:
            name = arg.arg
            if arg.annotation:
                ann = ast.unparse(arg.annotation) if hasattr(ast, "unparse") else "Any"
                args.append(f"{name}: {ann}")
            else:
                args.append(name)
        ret = ""
        if node.returns:
            ret = f" -> {ast.unparse(node.returns) if hasattr(ast, 'unparse') else 'Any'}"
        return f"({', '.join(args)}){ret}"

    def visit_ClassDef(self, node: ast.ClassDef):
        class_name = node.name
        qualified_id = f"{self.current_scope[0]}::{class_name}"
        source = self._get_node_source(node)
        doc = ast.get_docstring(node)

        state = ASTNodeState(
            node_id=qualified_id,
            node_type="class",
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=f"class {class_name}",
            docstring=doc,
            body_hash=self._hash_content(source),
            interface_contract=f"class {class_name}:\n    '''{doc or ''}'''"
        )
        self.nodes[qualified_id] = state

        # Entra no escopo da classe
        self.current_scope.append(class_name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool):
        fn_name = node.name
        if len(self.current_scope) > 1:
            # Método de classe
            qualified_id = f"{self.current_scope[0]}::{'.'.join(self.current_scope[1:])}.{fn_name}"
            node_type = "method"
        else:
            # Função top-level
            qualified_id = f"{self.current_scope[0]}::{fn_name}"
            node_type = "function"

        sig = self._format_signature(node)
        prefix = "async def " if is_async else "def "
        source = self._get_node_source(node)
        doc = ast.get_docstring(node)

        state = ASTNodeState(
            node_id=qualified_id,
            node_type=node_type,
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=f"{prefix}{fn_name}{sig}",
            docstring=doc,
            body_hash=self._hash_content(source),
            interface_contract=f"{prefix}{fn_name}{sig}"
        )
        self.nodes[qualified_id] = state

        # Inspeciona chamadas feitas dentro desta função
        self.calls_in_node[qualified_id] = set()
        old_scope = list(self.current_scope)
        self.current_scope.append(fn_name)
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = ""
                if isinstance(child.func, ast.Name):
                    call_name = child.func.id
                elif isinstance(child.func, ast.Attribute):
                    call_name = child.func.attr
                if call_name:
                    self.calls_in_node[qualified_id].add(call_name)
        self.current_scope = old_scope


class TopologicalStateGraph:
    """Grafo de Estado Topológico global da base de código."""

    def __init__(self, root_dir: Path | str):
        self.root_dir = Path(root_dir)
        self.nodes: Dict[str, ASTNodeState] = {}
        self.file_to_nodes: Dict[str, Set[str]] = {}

    def index_file(self, file_path: Path | str):
        path = Path(file_path)
        if not path.is_absolute():
            abs_path = self.root_dir / path
        else:
            abs_path = path
            path = abs_path.relative_to(self.root_dir)

        if not abs_path.exists() or abs_path.suffix != ".py":
            return

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            tree = ast.parse(content, filename=str(path))
        except Exception:
            return  # Ignora arquivos com erro de sintaxe temporário

        rel_str = path.as_posix()
        # Remove nós antigos deste arquivo se já indexado
        if rel_str in self.file_to_nodes:
            for old_id in self.file_to_nodes[rel_str]:
                if old_id in self.nodes:
                    del self.nodes[old_id]

        visitor = CodebaseASTVisitor(rel_str, content)
        visitor.visit(tree)

        self.file_to_nodes[rel_str] = set(visitor.nodes.keys())
        for nid, nstate in visitor.nodes.items():
            self.nodes[nid] = nstate

        # Resolve arestas de dependência simples por nome
        for caller_id, called_names in visitor.calls_in_node.items():
            for target_name in called_names:
                for cand_id in self.nodes:
                    if cand_id.endswith(f"::{target_name}") or cand_id.endswith(f".{target_name}"):
                        self.nodes[caller_id].dependencies.add(cand_id)
                        self.nodes[cand_id].dependents.add(caller_id)

    def index_codebase(self, max_files: int = 100):
        """Indexa incrementalmente os arquivos Python do projeto."""
        py_files = list(self.root_dir.glob("**/*.py"))
        for py_path in py_files[:max_files]:
            parts = py_path.parts
            if ".venv" in parts or "__pycache__" in parts or ".git" in parts:
                continue
            self.index_file(py_path)

    def get_node(self, node_id: str) -> Optional[ASTNodeState]:
        return self.nodes.get(node_id)

    def find_nodes_by_name(self, query: str) -> List[ASTNodeState]:
        q = query.lower()
        return [node for nid, node in self.nodes.items() if q in nid.lower()]
