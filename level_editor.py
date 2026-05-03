"""
level_editor.py
Editor de fases com grade clicável, seleção de cores e salvamento em levels.json.
"""

import json
import os
from panda3d.core import CardMaker, TextNode, TransparencyAttrib, LineSegs
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel,
    DirectEntry, DirectOptionMenu, DirectScrolledList,
)

LEVELS_PATH = os.path.join(os.path.dirname(__file__), "levels.json")

COLOR_PALETTE = {
    0:  (0.15, 0.15, 0.15, 1.0),  # vazio
    1:  (1.0, 0.2, 0.2, 1.0),
    2:  (0.2, 0.5, 1.0, 1.0),
    3:  (1.0, 1.0, 0.2, 1.0),
    4:  (0.2, 0.9, 0.3, 1.0),
    5:  (0.9, 0.4, 0.1, 1.0),
    6:  (0.7, 0.2, 0.9, 1.0),
    7:  (0.2, 0.9, 0.9, 1.0),
    8:  (1.0, 0.5, 0.7, 1.0),
    9:  (0.5, 0.3, 0.1, 1.0),
    10: (0.9, 0.9, 0.9, 1.0),
}

COLOR_NAMES = {
    0: "Vazio",
    1: "Vermelho",
    2: "Azul",
    3: "Amarelo",
    4: "Verde",
    5: "Laranja",
    6: "Roxo",
    7: "Ciano",
    8: "Rosa",
    9: "Marrom",
    10: "Branco",
}


def load_levels() -> list[dict]:
    if not os.path.exists(LEVELS_PATH):
        return []
    with open(LEVELS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_levels(levels: list[dict]) -> None:
    with open(LEVELS_PATH, "w", encoding="utf-8") as f:
        json.dump(levels, f, indent=2, ensure_ascii=False)


class LevelEditor:
    """Interface de edição de fases."""

    CELL_PX = 0.12   # tamanho de cada célula em coordenadas 2D

    def __init__(self, base, on_exit_callback):
        self.base = base
        self.on_exit = on_exit_callback

        self.levels = load_levels()
        self.editing_level: dict | None = None  # fase em edição
        self.grid_rows = 5
        self.grid_cols = 5
        self.matrix: list[list[int]] = []
        self.selected_color = 1

        self.root = base.aspect2d.attachNewNode("editor_root")
        self._show_level_list()

    # ── LISTA DE FASES ───────────────────────────────────────────────────────

    def _show_level_list(self):
        self._clear()

        self.bg = DirectFrame(
            frameColor=(0.1, 0.1, 0.15, 0.95),
            frameSize=(-1.6, 1.6, -1.0, 1.0),
            parent=self.root,
        )

        DirectLabel(
            text="EDITOR DE FASES", scale=0.1,
            pos=(0, 0, 0.82),
            text_fg=(0.9, 0.7, 0.1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.bg,
        )

        DirectButton(
            text="+ Nova Fase", scale=0.07,
            pos=(-0.9, 0, 0.65),
            command=self._new_level,
            parent=self.bg,
        )

        DirectButton(
            text="Voltar", scale=0.065,
            pos=(1.1, 0, 0.65),
            command=self._exit,
            parent=self.bg,
        )

        # Lista de fases existentes
        y = 0.45
        for lvl in self.levels:
            stars_data = ""
            row = DirectFrame(
                frameColor=(0.2, 0.2, 0.3, 0.8),
                frameSize=(-1.3, 1.3, -0.07, 0.07),
                pos=(0, 0, y),
                parent=self.bg,
            )

            DirectLabel(
                text=f"#{lvl['id']} — {lvl['name']}",
                scale=0.06, pos=(-0.8, 0, -0.02),
                text_fg=(1, 1, 1, 1),
                frameColor=(0, 0, 0, 0),
                parent=row,
            )

            lvl_ref = lvl  # captura para closure
            DirectButton(
                text="Editar", scale=0.055,
                pos=(0.7, 0, -0.02),
                command=lambda l=lvl_ref: self._edit_level(l),
                parent=row,
            )
            DirectButton(
                text="Jogar", scale=0.055,
                pos=(0.95, 0, -0.02),
                command=lambda l=lvl_ref: self._play_level(l),
                parent=row,
            )
            DirectButton(
                text="✕", scale=0.055,
                pos=(1.18, 0, -0.02),
                text_fg=(1, 0.3, 0.3, 1),
                command=lambda l=lvl_ref: self._delete_level(l),
                parent=row,
            )

            y -= 0.18
            if y < -0.85:
                break

    # ── CRIAÇÃO / EDIÇÃO ─────────────────────────────────────────────────────

    def _new_level(self):
        """Cria uma fase vazia."""
        new_id = max((l["id"] for l in self.levels), default=0) + 1
        lvl = {
            "id": new_id,
            "name": f"Fase {new_id}",
            "grid_size": [5, 5],
            "matrix": [[0]*5 for _ in range(5)],
            "colors": {str(i): list(COLOR_PALETTE[i]) for i in range(1, 11)},
            "time_3stars": 30,
            "time_2stars": 60,
            "time_1star": 90,
        }
        self._edit_level(lvl, is_new=True)

    def _edit_level(self, lvl: dict, is_new: bool = False):
        self._clear()
        self.editing_level = lvl
        self.is_new = is_new
        self.grid_rows = lvl["grid_size"][0]
        self.grid_cols = lvl["grid_size"][1]
        self.matrix = [row[:] for row in lvl["matrix"]]
        self._build_editor_ui()

    def _build_editor_ui(self):
        """Monta a interface de edição da grade."""
        self.bg = DirectFrame(
            frameColor=(0.08, 0.08, 0.12, 0.97),
            frameSize=(-1.6, 1.6, -1.0, 1.0),
            parent=self.root,
        )

        # Título e nome
        DirectLabel(
            text="EDITANDO FASE", scale=0.08,
            pos=(-0.6, 0, 0.88),
            text_fg=(0.9, 0.7, 0.1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.bg,
        )

        self.name_entry = DirectEntry(
            initialText=self.editing_level["name"],
            scale=0.07, pos=(0.2, 0, 0.83),
            width=10, numLines=1,
            parent=self.bg,
        )

        # Grade de edição
        self.cell_buttons: dict[tuple, DirectButton] = {}
        cs = self.CELL_PX
        total_w = self.grid_cols * cs
        total_h = self.grid_rows * cs
        origin_x = -total_w / 2
        origin_z = total_h / 2

        grid_frame = DirectFrame(
            frameColor=(0, 0, 0, 0),
            pos=(-0.35, 0, 0.0),
            parent=self.bg,
        )

        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                x = origin_x + c * cs + cs/2
                z = origin_z - r * cs - cs/2
                val = self.matrix[r][c]
                color = COLOR_PALETTE.get(val, COLOR_PALETTE[0])
                btn = DirectButton(
                    frameColor=color,
                    frameSize=(-cs/2+0.005, cs/2-0.005, -cs/2+0.005, cs/2-0.005),
                    pos=(x, 0, z),
                    relief=1,
                    command=self._cell_clicked,
                    extraArgs=[r, c],
                    parent=grid_frame,
                )
                self.cell_buttons[(r, c)] = btn

        # Seletor de cores
        self._build_color_picker()

        # Config de tamanho
        DirectLabel(
            text="Linhas:", scale=0.055, pos=(0.75, 0, 0.55),
            text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0),
            parent=self.bg,
        )
        self.rows_entry = DirectEntry(
            initialText=str(self.grid_rows),
            scale=0.065, pos=(0.75, 0, 0.42),
            width=3, numLines=1, parent=self.bg,
        )

        DirectLabel(
            text="Colunas:", scale=0.055, pos=(1.1, 0, 0.55),
            text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0),
            parent=self.bg,
        )
        self.cols_entry = DirectEntry(
            initialText=str(self.grid_cols),
            scale=0.065, pos=(1.1, 0, 0.42),
            width=3, numLines=1, parent=self.bg,
        )

        DirectButton(
            text="Redimensionar", scale=0.055,
            pos=(0.92, 0, 0.28),
            command=self._resize_grid,
            parent=self.bg,
        )

        # Tempos de estrela
        DirectLabel(text="⭐⭐⭐ (seg):", scale=0.055, pos=(0.75, 0, 0.08),
                    text_fg=(1, 1, 0.2, 1), frameColor=(0, 0, 0, 0), parent=self.bg)
        self.t3_entry = DirectEntry(
            initialText=str(self.editing_level["time_3stars"]),
            scale=0.065, pos=(0.75, 0, -0.05), width=5, numLines=1, parent=self.bg)

        DirectLabel(text="⭐⭐ (seg):", scale=0.055, pos=(1.15, 0, 0.08),
                    text_fg=(0.8, 0.8, 0.2, 1), frameColor=(0, 0, 0, 0), parent=self.bg)
        self.t2_entry = DirectEntry(
            initialText=str(self.editing_level["time_2stars"]),
            scale=0.065, pos=(1.15, 0, -0.05), width=5, numLines=1, parent=self.bg)

        DirectLabel(text="⭐ (seg):", scale=0.055, pos=(0.95, 0, -0.2),
                    text_fg=(0.6, 0.6, 0.2, 1), frameColor=(0, 0, 0, 0), parent=self.bg)
        self.t1_entry = DirectEntry(
            initialText=str(self.editing_level["time_1star"]),
            scale=0.065, pos=(0.95, 0, -0.33), width=5, numLines=1, parent=self.bg)

        # Botões de ação
        DirectButton(
            text="Salvar", scale=0.07, pos=(0.75, 0, -0.6),
            command=self._save_level, parent=self.bg,
        )
        DirectButton(
            text="Cancelar", scale=0.07, pos=(1.15, 0, -0.6),
            command=self._show_level_list, parent=self.bg,
        )

    def _build_color_picker(self):
        """
        Seletor de cores na lateral direita da tela.
        10 cores + opção apagar (0), dispostas em grid 3 colunas.
        A cor selecionada tem borda destacada.
        """
        # Título
        DirectLabel(
            text="PALHETA", scale=0.055,
            pos=(1.0, 0, 0.62),
            text_fg=(1, 1, 0.5, 1), frameColor=(0, 0, 0, 0),
            parent=self.bg,
        )

        # Todas as cores incluindo "borracha" (0 = apagar)
        all_colors = [(0, COLOR_PALETTE[0], "Apagar")] + \
                     [(cid, COLOR_PALETTE[cid], COLOR_NAMES[cid])
                      for cid in range(1, 11)]

        self._color_btns: dict[int, DirectButton] = {}
        BTN_SIZE = 0.085
        COLS = 3
        START_X = 0.82
        START_Z = 0.50
        GAP = 0.095

        for idx, (cid, col, name) in enumerate(all_colors):
            col_i = idx % COLS
            row_i = idx // COLS
            x = START_X + col_i * GAP
            z = START_Z - row_i * GAP

            btn = DirectButton(
                frameColor=col,
                frameSize=(-BTN_SIZE/2, BTN_SIZE/2, -BTN_SIZE/2, BTN_SIZE/2),
                pos=(x, 0, z),
                relief=2,  # groove — dá efeito 3D
                borderWidth=(0.008, 0.008),
                command=self._select_color,
                extraArgs=[cid],
                parent=self.bg,
            )
            self._color_btns[cid] = btn

        # Label da cor selecionada
        self.selected_color_label = DirectLabel(
            text=f"● {COLOR_NAMES.get(self.selected_color, '?')}",
            scale=0.052,
            pos=(1.0, 0, -0.28),
            text_fg=COLOR_PALETTE.get(self.selected_color, (1, 1, 1, 1)),
            frameColor=(0.15, 0.15, 0.2, 0.9),
            frameSize=(-0.28, 0.28, -0.06, 0.07),
            parent=self.bg,
        )

        # Destaca cor já selecionada
        self._highlight_selected_btn()

    def _highlight_selected_btn(self):
        """Coloca borda branca no botão da cor selecionada."""
        for cid, btn in self._color_btns.items():
            if cid == self.selected_color:
                btn["relief"] = 1
                btn["borderWidth"] = (0.016, 0.016)
                btn["frameColor"] = tuple(
                    min(c + 0.35, 1.0) if i < 3 else v
                    for i, (c, v) in enumerate(
                        zip(COLOR_PALETTE.get(cid, (0.5,)*4),
                            COLOR_PALETTE.get(cid, (0.5,)*4))
                    )
                )
                # Adiciona marcador "selecionado" com texto
                btn["text"] = "✓"
                btn["text_scale"] = 0.055
                btn["text_fg"] = (1, 1, 1, 1)
            else:
                btn["relief"] = 2
                btn["borderWidth"] = (0.006, 0.006)
                btn["frameColor"] = COLOR_PALETTE.get(cid, (0.5, 0.5, 0.5, 1))
                btn["text"] = ""

    def _select_color(self, cid: int):
        self.selected_color = cid
        col = COLOR_PALETTE.get(cid, (1, 1, 1, 1))
        self.selected_color_label["text"] = f"● {COLOR_NAMES.get(cid, str(cid))}"
        self.selected_color_label["text_fg"] = col
        self._highlight_selected_btn()

    def _cell_clicked(self, row: int, col: int):
        """Clique em uma célula da grade alterna sua cor."""
        current = self.matrix[row][col]
        # Se já tem a cor selecionada, limpa; senão aplica
        if current == self.selected_color:
            self.matrix[row][col] = 0
            new_color = COLOR_PALETTE[0]
        else:
            self.matrix[row][col] = self.selected_color
            new_color = COLOR_PALETTE.get(self.selected_color, COLOR_PALETTE[1])

        btn = self.cell_buttons.get((row, col))
        if btn:
            btn["frameColor"] = new_color

    def _resize_grid(self):
        """Redimensiona a grade."""
        try:
            new_r = int(self.rows_entry.get())
            new_c = int(self.cols_entry.get())
        except ValueError:
            return

        new_r = max(2, min(new_r, 10))
        new_c = max(2, min(new_c, 10))

        # Preserva conteúdo existente
        new_matrix = [[0]*new_c for _ in range(new_r)]
        for r in range(min(new_r, self.grid_rows)):
            for c in range(min(new_c, self.grid_cols)):
                new_matrix[r][c] = self.matrix[r][c]

        self.grid_rows = new_r
        self.grid_cols = new_c
        self.matrix = new_matrix
        self._clear()
        self._build_editor_ui()

    def _save_level(self):
        """Salva a fase editada em levels.json."""
        name = self.name_entry.get().strip() or self.editing_level["name"]
        try:
            t3 = int(self.t3_entry.get())
            t2 = int(self.t2_entry.get())
            t1 = int(self.t1_entry.get())
        except ValueError:
            t3, t2, t1 = 30, 60, 90

        self.editing_level["name"] = name
        self.editing_level["grid_size"] = [self.grid_rows, self.grid_cols]
        self.editing_level["matrix"] = [row[:] for row in self.matrix]
        self.editing_level["time_3stars"] = t3
        self.editing_level["time_2stars"] = t2
        self.editing_level["time_1star"] = t1
        self.editing_level["colors"] = {
            str(i): list(COLOR_PALETTE[i]) for i in range(1, 11)
        }

        if self.is_new:
            self.levels.append(self.editing_level)
        else:
            for i, lvl in enumerate(self.levels):
                if lvl["id"] == self.editing_level["id"]:
                    self.levels[i] = self.editing_level
                    break

        save_levels(self.levels)
        self._show_level_list()

    def _delete_level(self, lvl: dict):
        self.levels = [l for l in self.levels if l["id"] != lvl["id"]]
        save_levels(self.levels)
        self._show_level_list()

    def _play_level(self, lvl: dict):
        """Inicia jogo a partir do editor."""
        from game import Game
        self.cleanup()
        Game(self.base, lvl["id"], 0, self.on_exit)

    # ── UTILS ────────────────────────────────────────────────────────────────

    def _clear(self):
        """Remove todos os elementos visuais."""
        for child in self.root.getChildren():
            child.removeNode()
        # Remove gui
        for attr in ["bg", "name_entry", "rows_entry", "cols_entry",
                     "t3_entry", "t2_entry", "t1_entry"]:
            if hasattr(self, attr):
                obj = getattr(self, attr)
                if obj:
                    try:
                        obj.destroy()
                    except Exception:
                        pass

    def _exit(self):
        self.cleanup()
        self.on_exit()

    def cleanup(self):
        self._clear()
        if hasattr(self, "root"):
            self.root.removeNode()