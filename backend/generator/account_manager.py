"""
Módulo para gestionar y rotar múltiples sesiones de ChatGPT/Lovable.
"""

import os
import json
from pathlib import Path
from typing import List, Optional

SESSIONS_DIR = Path("config/sessions")
ACCOUNTS_COUNT = 6


class AccountManager:
    def __init__(self, count: int = ACCOUNTS_COUNT):
        self.count = count
        self.sessions_dir = SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_index_file = self.sessions_dir / "current_index.json"

    def _get_current_index(self) -> int:
        """Obtiene el índice de la última cuenta usada."""
        if self.current_index_file.exists():
            try:
                with open(self.current_index_file, "r") as f:
                    return json.load(f).get("index", 0)
            except:
                return 0
        return 0

    def _save_current_index(self, index: int):
        """Guarda el índice de la cuenta actual."""
        with open(self.current_index_file, "w") as f:
            json.dump({"index": index}, f)

    def get_next_account(self) -> dict:
        """
        Calcula y retorna la siguiente cuenta disponible para rotación.
        Retorna un dict con el path de la sesión y el ID.
        """
        current = self._get_current_index()
        next_index = (current + 1) % self.count
        self._save_current_index(next_index)

        account_id = f"account_{next_index +1 }"
        session_path = self.sessions_dir / account_id
        session_path.mkdir(exist_ok=True)

        return {
            "id": account_id,
            "path": str(session_path.absolute()),
            "index": next_index,
        }

    def get_all_accounts(self) -> List[dict]:
        """Lista todas las cuentas registradas."""
        accounts = []
        for i in range(self.count):
            account_id = f"account_{i +1 }"
            accounts.append(
                {
                    "id": account_id,
                    "path": str((self.sessions_dir / account_id).absolute()),
                }
            )
        return accounts


if __name__ == "__main__":

    am = AccountManager()
    print("--- ROTACIÓN DE CUENTAS ---")
    for _ in range(3):
        print(f"Siguiente: {am .get_next_account ()}")
