"""
block_utils.py
Utilitários para analisar matrizes de fases e extrair blocos conectados.
"""

from collections import deque
import random


def find_connected_blocks(matrix: list[list[int]]) -> list[dict]:
    """
    Dado uma matriz 2D, encontra todos os grupos de células conectadas
    com o mesmo valor (ignorando 0).
    Retorna lista de dicts:
      {
        'color_id': int,
        'cells': [(row, col), ...],   # células relativas à matriz
        'shape': [(dr, dc), ...],     # células relativas ao pivot (centro do grupo)
      }
    """
    rows = len(matrix)
    cols = len(matrix[0]) if rows > 0 else 0
    visited = [[False] * cols for _ in range(rows)]
    blocks = []

    for r in range(rows):
        for c in range(cols):
            val = matrix[r][c]
            if val == 0 or visited[r][c]:
                continue
            # BFS
            group_cells = []
            queue = deque([(r, c)])
            visited[r][c] = True
            while queue:
                cr, cc = queue.popleft()
                group_cells.append((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if not visited[nr][nc] and matrix[nr][nc] == val:
                            visited[nr][nc] = True
                            queue.append((nr, nc))

            # Calcula shape relativo ao pivot (menor r, menor c do grupo)
            min_r = min(cell[0] for cell in group_cells)
            min_c = min(cell[1] for cell in group_cells)
            shape = [(cr - min_r, cc - min_c) for cr, cc in group_cells]

            blocks.append({
                "color_id": val,
                "cells": group_cells,
                "shape": shape,
                "pivot_row": min_r,
                "pivot_col": min_c,
            })

    return blocks


def blocks_to_queue(blocks: list[dict], shuffle: bool = True) -> list[dict]:
    """
    Recebe lista de blocos e retorna uma fila de blocos para atirar.
    Se shuffle=True, ordena aleatoriamente.
    """
    queue = list(blocks)
    if shuffle:
        random.shuffle(queue)
    return queue


def rotate_shape_cw(shape: list[tuple]) -> list[tuple]:
    """Rotaciona o shape 90° horário: (r, c) → (c, max_r - r)."""
    if not shape:
        return shape
    max_r = max(r for r, c in shape)
    rotated = [(c, max_r - r) for r, c in shape]
    # Normaliza para mínimos zero
    min_r = min(r for r, c in rotated)
    min_c = min(c for r, c in rotated)
    return [(r - min_r, c - min_c) for r, c in rotated]


def rotate_shape_ccw(shape: list[tuple]) -> list[tuple]:
    """Rotaciona o shape 90° anti-horário: (r, c) → (max_c - c, r)."""
    if not shape:
        return shape
    max_c = max(c for r, c in shape)
    rotated = [(max_c - c, r) for r, c in shape]
    min_r = min(r for r, c in rotated)
    min_c = min(c for r, c in rotated)
    return [(r - min_r, c - min_c) for r, c in rotated]


def can_place(matrix: list[list[int]], shape: list[tuple],
              pivot_r: int, pivot_c: int, color_id: int) -> bool:
    """
    Verifica se o bloco pode ser colocado na posição (pivot_r, pivot_c) na matriz.
    Retorna True se TODAS as células do shape batem com o color_id na matriz.
    """
    rows = len(matrix)
    cols = len(matrix[0]) if rows > 0 else 0
    for dr, dc in shape:
        r, c = pivot_r + dr, pivot_c + dc
        if not (0 <= r < rows and 0 <= c < cols):
            return False
        if matrix[r][c] != color_id:
            return False
    return True


def get_shape_bounds(shape: list[tuple]) -> tuple[int, int, int, int]:
    """Retorna (min_r, min_c, max_r, max_c) do shape."""
    rs = [r for r, c in shape]
    cs = [c for r, c in shape]
    return min(rs), min(cs), max(rs), max(cs)
