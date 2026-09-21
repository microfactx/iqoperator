"""Sync opcional de logs/trades para um dataset do Hugging Face (bucket).

Usa HF_TOKEN + HF_DATASET_REPO (ex: microfactx/iqoperator-trades).
Se não configurado, vira no-op. Fail-open: nunca quebra o bot.

Railway sem disco: ative isso e o trades_live.csv sobrevive a restarts.
"""
import logging
import os
import threading
import time

log = logging.getLogger("iqrobot.hf")


def _configured() -> bool:
    return bool(os.getenv("HF_TOKEN") and os.getenv("HF_DATASET_REPO"))


def sync_file(local_path: str, repo_path: str | None = None):
    """Upload em thread daemon; silencioso se não configurado."""
    if not _configured():
        return
    if not os.path.exists(local_path):
        return
    repo_path = repo_path or os.path.basename(local_path)
    token = os.getenv("HF_TOKEN", "")
    repo_id = os.getenv("HF_DATASET_REPO", "")

    def _do():
        try:
            from huggingface_hub import HfApi
            api = HfApi(token=token)
            # garante dataset existe (cria se faltar, idempotente)
            try:
                api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
            except Exception:
                pass
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=repo_path,
                repo_id=repo_id,
                repo_type="dataset",
            )
            log.info(f"[HF SYNC] {local_path} -> {repo_id}/{repo_path}")
        except Exception as e:
            log.warning(f"[HF SYNC] falhou {local_path}: {e}")

    threading.Thread(target=_do, daemon=True).start()
