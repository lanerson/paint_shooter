"""
save_manager.py
Gerencia os 3 slots de save do jogo.
"""

import json
import os

SAVE_DIR = os.path.join(os.path.dirname(__file__), "saves")
NUM_SLOTS = 3


def _slot_path(slot: int) -> str:
    os.makedirs(SAVE_DIR, exist_ok=True)
    return os.path.join(SAVE_DIR, f"save_{slot}.json")


def load_save(slot: int) -> dict | None:
    """Retorna os dados do save ou None se vazio."""
    path = _slot_path(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_save(slot: int, data: dict) -> None:
    """Salva os dados no slot especificado."""
    path = _slot_path(slot)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def delete_save(slot: int) -> None:
    """Apaga o save do slot."""
    path = _slot_path(slot)
    if os.path.exists(path):
        os.remove(path)


def all_saves() -> list[dict | None]:
    """Retorna lista com dados dos 3 slots (None se vazio)."""
    return [load_save(i) for i in range(NUM_SLOTS)]


def new_save(slot: int, player_name: str = "Jogador") -> dict:
    """Cria um save novo e grava no slot."""
    data = {
        "player_name": player_name,
        "current_level": 1,
        "levels_progress": {},  # {level_id: {"stars": N, "best_time": T}}
        "total_stars": 0,
    }
    write_save(slot, data)
    return data


def update_level_progress(slot: int, level_id: int, stars: int, time_taken: float) -> None:
    """Atualiza o progresso de uma fase no save."""
    data = load_save(slot)
    if data is None:
        return
    key = str(level_id)
    prev = data["levels_progress"].get(key, {"stars": 0, "best_time": float("inf")})
    # Só sobrescreve se melhorou
    if stars > prev["stars"] or (stars == prev["stars"] and time_taken < prev["best_time"]):
        data["levels_progress"][key] = {"stars": stars, "best_time": round(time_taken, 2)}
    # Avança fase se necessário
    if level_id >= data["current_level"]:
        data["current_level"] = level_id + 1
    # Recalcula estrelas totais
    data["total_stars"] = sum(v["stars"] for v in data["levels_progress"].values())
    write_save(slot, data)
