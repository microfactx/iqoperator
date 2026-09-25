"""
Deterministic Sandbox Runner.
Executes code mutations locally in a clean sandbox, filtering 99% of terminal noise.
"""

from __future__ import annotations
import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class SandboxResult:
    success: bool
    diagnostic_tuple: str     # Tupla simbólica concisa (ex: "ERR_ASSERT[test_auth, Expected 200 Got 401]")
    raw_output_size: int      # Tamanho original da saída em bytes
    compressed_token_size: int # Tokens consumidos pelo diagnóstico filtrado


class DeterministicSandbox:
    """Executa verificações locais e comprime erros em sinais simbólicos discretos."""

    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root)

    def check_python_syntax(self, code_str: str) -> Tuple[bool, str]:
        """Validação determinística de sintaxe sem envolver LLM."""
        try:
            ast.parse(code_str)
            return True, "SYNTAX_OK"
        except SyntaxError as e:
            return False, f"ERR_SYNTAX[L{e.lineno}:C{e.offset} - {e.msg}]"

    def run_isolated_command(self, cmd: list[str], timeout_sec: int = 15) -> SandboxResult:
        """Executa um comando local e comprime o resultado sem vazar logs extensos."""
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.workspace_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec
            )
            raw_len = len(res.stdout) + len(res.stderr)

            if res.returncode == 0:
                diag = "EXEC_OK[Code 0]"
                success = True
            else:
                success = False
                diag = self._distill_error_output(res.stdout, res.stderr)

            tokens = max(1, len(diag) // 4)
            return SandboxResult(
                success=success,
                diagnostic_tuple=diag,
                raw_output_size=raw_len,
                compressed_token_size=tokens
            )
        except subprocess.TimeoutExpired:
            diag = f"ERR_TIMEOUT[{timeout_sec}s]"
            return SandboxResult(success=False, diagnostic_tuple=diag, raw_output_size=0, compressed_token_size=4)
        except Exception as e:
            diag = f"ERR_EXEC[{type(e).__name__}: {str(e)[:40]}]"
            return SandboxResult(success=False, diagnostic_tuple=diag, raw_output_size=0, compressed_token_size=6)

    def _distill_error_output(self, stdout: str, stderr: str) -> str:
        """Filtra 99% do lixo de traceback e extrai apenas a linha fatal."""
        combined = (stderr + "\n" + stdout).strip()
        lines = [line.strip() for line in combined.splitlines() if line.strip()]

        if not lines:
            return "ERR_FAIL[Unknown failure]"

        # Procura por linhas de erro clássicas (AssertionError, ValueError, etc)
        for line in reversed(lines):
            for err_tag in ["AssertionError", "SyntaxError", "TypeError", "ValueError", "ImportError", "FAILED"]:
                if err_tag in line:
                    clean = line.replace("AssertionError:", "").strip()
                    return f"ERR_{err_tag.upper()}[{clean[:60]}]"

        # Se não achar um erro padrão, pega a última linha útil
        last_line = lines[-1][:60]
        return f"ERR_GENERIC[{last_line}]"
