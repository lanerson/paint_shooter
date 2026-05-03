"""
menu.py
Menu principal: Novo Jogo, Continuar, Criar Fase, Configurações, Sair.
"""

import json
import os
from panda3d.core import CardMaker, TextNode, TransparencyAttrib
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectLabel, DirectEntry,
    DirectSlider, DirectOptionMenu,
)
from sound_manager import SoundManager
import save_manager

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_KEYS = {
    "shoot": "space",
    "rotate_left": "a",
    "rotate_right": "d",
    "move_left": "arrow_left",
    "move_right": "arrow_right",
    "move_up": "arrow_up",
    "move_down": "arrow_down",
    "pause": "escape",
}


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"keybindings": DEFAULT_KEYS, "audio": {}, "graphics": {}}


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


class Menu:
    """Controlador do menu principal."""

    def __init__(self, base):
        self.base = base
        self.config = load_config()
        self.root = base.aspect2d.attachNewNode("menu_root")
        self._show_main()
        SoundManager.play_music("menu")

    # ── TELA PRINCIPAL ───────────────────────────────────────────────────────

    def _show_main(self):
        self._clear()

        self.bg = DirectFrame(
            frameColor=(0.05, 0.05, 0.1, 1.0),
            frameSize=(-1.8, 1.8, -1.1, 1.1),
            parent=self.root,
        )

        # Título
        DirectLabel(
            text="PAINT SHOOTER",
            scale=0.18,
            pos=(0, 0, 0.65),
            text_fg=(0.9, 0.7, 0.1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.bg,
        )
        DirectLabel(
            text="Pinte o mundo a balas!",
            scale=0.07,
            pos=(0, 0, 0.48),
            text_fg=(0.7, 0.7, 0.7, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.bg,
        )

        btn_style = dict(
            scale=0.09,
            frameColor=(0.15, 0.15, 0.25, 0.9),
            text_fg=(1, 1, 1, 1),
            frameSize=(-2.2, 2.2, -0.5, 0.7),
            relief=1,
        )

        DirectButton(
            text="NOVO JOGO",
            pos=(0, 0, 0.2),
            command=self._show_save_select,
            extraArgs=["new"],
            parent=self.bg,
            **btn_style,
        )
        DirectButton(
            text="CONTINUAR",
            pos=(0, 0, -0.0),
            command=self._show_save_select,
            extraArgs=["continue"],
            parent=self.bg,
            **btn_style,
        )
        DirectButton(
            text="CRIAR FASE",
            pos=(0, 0, -0.2),
            command=self._open_editor,
            parent=self.bg,
            **btn_style,
        )
        DirectButton(
            text="CONFIGURAÇÕES",
            pos=(0, 0, -0.4),
            command=self._show_settings,
            parent=self.bg,
            **btn_style,
        )
        DirectButton(
            text="SAIR",
            pos=(0, 0, -0.6),
            command=self.base.userExit,
            parent=self.bg,
            **btn_style,
        )

    # ── SELEÇÃO DE SAVE ──────────────────────────────────────────────────────

    def _show_save_select(self, mode: str):
        """Exibe os 3 slots de save."""
        SoundManager.play("menu_click")
        self._clear()
        self._mode = mode

        self.bg = DirectFrame(
            frameColor=(0.05, 0.05, 0.1, 1.0),
            frameSize=(-1.8, 1.8, -1.1, 1.1),
            parent=self.root,
        )

        title = "NOVO JOGO — Escolha o Save" if mode == "new" else "CONTINUAR — Escolha o Save"
        DirectLabel(
            text=title, scale=0.09, pos=(0, 0, 0.82),
            text_fg=(0.9, 0.7, 0.1, 1), frameColor=(0, 0, 0, 0),
            parent=self.bg,
        )

        saves = save_manager.all_saves()

        for slot_idx, save_data in enumerate(saves):
            y = 0.45 - slot_idx * 0.45

            slot_frame = DirectFrame(
                frameColor=(0.15, 0.15, 0.25, 0.9),
                frameSize=(-1.4, 1.4, -0.18, 0.18),
                pos=(0, 0, y),
                parent=self.bg,
            )

            if save_data is None:
                # Slot vazio
                DirectLabel(
                    text=f"Save {slot_idx + 1}  —  [Vazio]",
                    scale=0.07, pos=(-0.5, 0, 0.0),
                    text_fg=(0.6, 0.6, 0.6, 1), frameColor=(0, 0, 0, 0),
                    parent=slot_frame,
                )
                if mode == "new":
                    DirectButton(
                        text="Usar este slot", scale=0.065,
                        pos=(0.8, 0, 0.0),
                        command=self._start_new_game,
                        extraArgs=[slot_idx],
                        parent=slot_frame,
                    )
            else:
                # Slot com dados
                stars = save_data.get("total_stars", 0)
                level = save_data.get("current_level", 1)
                name = save_data.get("player_name", "Jogador")
                DirectLabel(
                    text=f"Save {slot_idx + 1}  —  {name}",
                    scale=0.065, pos=(-0.7, 0, 0.07),
                    text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0),
                    parent=slot_frame,
                )
                DirectLabel(
                    text=f"Fase: {level}   ★ {stars}",
                    scale=0.058, pos=(-0.7, 0, -0.07),
                    text_fg=(0.8, 0.8, 0.4, 1), frameColor=(0, 0, 0, 0),
                    parent=slot_frame,
                )
                if mode == "new":
                    DirectButton(
                        text="Sobrescrever", scale=0.06,
                        pos=(0.8, 0, 0.0),
                        command=self._confirm_overwrite,
                        extraArgs=[slot_idx],
                        parent=slot_frame,
                    )
                else:
                    DirectButton(
                        text="Continuar", scale=0.065,
                        pos=(0.8, 0, 0.0),
                        command=self._continue_game,
                        extraArgs=[slot_idx, save_data],
                        parent=slot_frame,
                    )

        DirectButton(
            text="Voltar", scale=0.07, pos=(0, 0, -0.88),
            command=self._show_main, parent=self.bg,
        )

    def _confirm_overwrite(self, slot: int):
        """Dialogo de confirmação de sobrescrita."""
        confirm = DirectFrame(
            frameColor=(0.1, 0.05, 0.05, 0.95),
            frameSize=(-0.7, 0.7, -0.3, 0.3),
            pos=(0, 0, 0),
            parent=self.root,
        )
        DirectLabel(
            text="Este save será apagado!\nTem certeza?",
            scale=0.07, pos=(0, 0, 0.1),
            text_fg=(1, 0.5, 0.5, 1), frameColor=(0, 0, 0, 0),
            parent=confirm,
        )
        DirectButton(
            text="Sim, continuar", scale=0.07,
            pos=(-0.25, 0, -0.15),
            command=lambda: [confirm.destroy(), self._start_new_game(slot)],
            parent=confirm,
        )
        DirectButton(
            text="Cancelar", scale=0.07,
            pos=(0.28, 0, -0.15),
            command=confirm.destroy,
            parent=confirm,
        )

    def _start_new_game(self, slot: int):
        """Inicia um novo jogo no slot selecionado."""
        SoundManager.play("menu_click")
        save_manager.new_save(slot)
        self._launch_game(slot, 1)

    def _continue_game(self, slot: int, save_data: dict):
        """Abre tela de seleção de fase para o save escolhido."""
        SoundManager.play("menu_click")
        self._show_level_select(slot, save_data)

    def _show_level_select(self, slot: int, save_data: dict):
        """Tela de seleção de fase — mostra todas as fases com estrelas obtidas."""
        import json, os
        levels_path = os.path.join(os.path.dirname(__file__), "levels.json")
        with open(levels_path, "r", encoding="utf-8") as f:
            all_levels = json.load(f)

        self._clear()
        self._slot = slot
        self._save_data = save_data

        self.bg = DirectFrame(
            frameColor=(0.05, 0.05, 0.1, 1.0),
            frameSize=(-1.8, 1.8, -1.1, 1.1),
            parent=self.root,
        )

        DirectLabel(
            text="SELECIONAR FASE", scale=0.09, pos=(0, 0, 0.88),
            text_fg=(0.9, 0.7, 0.1, 1), frameColor=(0, 0, 0, 0),
            parent=self.bg,
        )

        progress = save_data.get("levels_progress", {})
        current_level = save_data.get("current_level", 1)

        # Grade de fases: 3 por linha
        COLS = 3
        CELL_W = 0.95
        CELL_H = 0.32
        START_X = -CELL_W
        START_Z = 0.58
        GAP_X   = CELL_W
        GAP_Z   = CELL_H + 0.06

        for idx, lvl in enumerate(all_levels):
            col_i = idx % COLS
            row_i = idx // COLS
            x = START_X + col_i * GAP_X
            z = START_Z - row_i * GAP_Z

            lvl_id    = lvl["id"]
            unlocked  = lvl_id <= current_level
            prog      = progress.get(str(lvl_id), {})
            stars     = prog.get("stars", 0)
            best_time = prog.get("best_time", None)

            frame_color = (0.15, 0.18, 0.28, 0.95) if unlocked else (0.1, 0.1, 0.12, 0.7)

            card = DirectFrame(
                frameColor=frame_color,
                frameSize=(-CELL_W/2 + 0.05, CELL_W/2 - 0.05, -CELL_H/2 + 0.02, CELL_H/2 - 0.02),
                pos=(x, 0, z),
                parent=self.bg,
            )

            # Nome da fase
            name_color = (1, 1, 1, 1) if unlocked else (0.45, 0.45, 0.45, 1)
            DirectLabel(
                text=lvl["name"], scale=0.055, pos=(0, 0, 0.07),
                text_fg=name_color, frameColor=(0, 0, 0, 0),
                parent=card,
            )

            if unlocked:
                # Estrelas
                star_str = ("★" * stars + "☆" * (3 - stars)) if stars > 0 else "☆☆☆"
                DirectLabel(
                    text=star_str, scale=0.07, pos=(0, 0, -0.02),
                    text_fg=(1, 0.85, 0.1, 1), frameColor=(0, 0, 0, 0),
                    parent=card,
                )
                # Melhor tempo
                if best_time is not None:
                    m = int(best_time) // 60; s = int(best_time) % 60
                    DirectLabel(
                        text=f"Melhor: {m:02d}:{s:02d}", scale=0.045, pos=(0, 0, -0.1),
                        text_fg=(0.6, 0.9, 0.6, 1), frameColor=(0, 0, 0, 0),
                        parent=card,
                    )
                # Botão jogar (clique no card inteiro)
                DirectButton(
                    frameColor=(0, 0, 0, 0),
                    frameSize=(-CELL_W/2 + 0.05, CELL_W/2 - 0.05, -CELL_H/2 + 0.02, CELL_H/2 - 0.02),
                    pos=(0, 0, 0), relief=0,
                    command=self._launch_game,
                    extraArgs=[slot, lvl_id],
                    parent=card,
                )
            else:
                DirectLabel(
                    text="🔒", scale=0.09, pos=(0, 0, -0.03),
                    text_fg=(0.4, 0.4, 0.4, 1), frameColor=(0, 0, 0, 0),
                    parent=card,
                )

        DirectButton(
            text="Voltar", scale=0.07, pos=(0, 0, -0.92),
            command=self._show_save_select,
            extraArgs=["continue"],
            parent=self.bg,
        )

    def _launch_game(self, slot: int, level_id: int):
        """Lança o jogo."""
        from game import Game
        self.cleanup()
        Game(self.base, level_id, slot, self._return_to_menu)

    def _return_to_menu(self):
        """Callback chamado pelo jogo ao sair."""
        self.__init__(self.base)

    # ── CONFIGURAÇÕES ────────────────────────────────────────────────────────

    def _show_settings(self):
        SoundManager.play("menu_click")
        self._clear()

        self.bg = DirectFrame(
            frameColor=(0.05, 0.05, 0.1, 1.0),
            frameSize=(-1.8, 1.8, -1.1, 1.1),
            parent=self.root,
        )

        DirectLabel(
            text="CONFIGURAÇÕES", scale=0.1, pos=(0, 0, 0.88),
            text_fg=(0.9, 0.7, 0.1, 1), frameColor=(0, 0, 0, 0),
            parent=self.bg,
        )

        # Tabs
        DirectButton(
            text="Controles", scale=0.07, pos=(-0.4, 0, 0.72),
            command=self._show_controls_settings, parent=self.bg,
        )
        DirectButton(
            text="Áudio", scale=0.07, pos=(0.1, 0, 0.72),
            command=self._show_audio_settings, parent=self.bg,
        )
        DirectButton(
            text="Voltar", scale=0.07, pos=(1.2, 0, 0.72),
            command=self._show_main, parent=self.bg,
        )

        self._settings_panel = DirectFrame(
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0),
            parent=self.bg,
        )

        self._show_controls_settings()

    def _show_controls_settings(self):
        """Painel de configuração de teclas."""
        if hasattr(self, "_settings_panel"):
            self._settings_panel.destroy()

        self._settings_panel = DirectFrame(
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0),
            parent=self.bg,
        )

        kb = self.config.get("keybindings", DEFAULT_KEYS)
        self.key_entries: dict[str, DirectEntry] = {}

        labels = {
            "shoot": "Atirar",
            "rotate_left": "Girar Esq.",
            "rotate_right": "Girar Dir.",
            "move_left": "Mover Esq.",
            "move_right": "Mover Dir.",
            "move_up": "Mover Cima",
            "move_down": "Mover Baixo",
            "pause": "Pausar",
        }

        y = 0.55
        for key, label in labels.items():
            DirectLabel(
                text=label + ":", scale=0.06, pos=(-0.5, 0, y),
                text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0),
                parent=self._settings_panel,
            )
            entry = DirectEntry(
                initialText=kb.get(key, DEFAULT_KEYS.get(key, "")),
                scale=0.065, pos=(0.2, 0, y - 0.01),
                width=10, numLines=1,
                parent=self._settings_panel,
            )
            self.key_entries[key] = entry
            y -= 0.13

        DirectButton(
            text="Salvar Controles", scale=0.07,
            pos=(0, 0, y - 0.1),
            command=self._save_controls,
            parent=self._settings_panel,
        )

    def _save_controls(self):
        """Salva as teclas configuradas."""
        kb = {key: entry.get().strip() for key, entry in self.key_entries.items()}
        self.config["keybindings"] = kb
        save_config(self.config)

    def _show_audio_settings(self):
        """Painel de configuração de áudio."""
        if hasattr(self, "_settings_panel"):
            self._settings_panel.destroy()

        self._settings_panel = DirectFrame(
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0),
            parent=self.bg,
        )

        audio = self.config.get("audio", {})

        DirectLabel(
            text="Volume Geral:", scale=0.07, pos=(-0.3, 0, 0.4),
            text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0),
            parent=self._settings_panel,
        )
        self.master_slider = DirectSlider(
            range=(0, 1), value=audio.get("master_volume", 1.0),
            pageSize=0.1, scale=0.6, pos=(0, 0, 0.22),
            command=self._update_volumes,
            parent=self._settings_panel,
        )

        DirectLabel(
            text="Efeitos Sonoros:", scale=0.07, pos=(-0.3, 0, 0.05),
            text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0),
            parent=self._settings_panel,
        )
        self.sfx_slider = DirectSlider(
            range=(0, 1), value=audio.get("sfx_volume", 1.0),
            pageSize=0.1, scale=0.6, pos=(0, 0, -0.13),
            command=self._update_volumes,
            parent=self._settings_panel,
        )

        DirectLabel(
            text="Música:", scale=0.07, pos=(-0.3, 0, -0.3),
            text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0),
            parent=self._settings_panel,
        )
        self.music_slider = DirectSlider(
            range=(0, 1), value=audio.get("music_volume", 0.7),
            pageSize=0.1, scale=0.6, pos=(0, 0, -0.48),
            command=self._update_volumes,
            parent=self._settings_panel,
        )

        DirectButton(
            text="Salvar Áudio", scale=0.07,
            pos=(0, 0, -0.68),
            command=self._save_audio,
            parent=self._settings_panel,
        )

    def _update_volumes(self):
        """Atualiza volumes em tempo real."""
        if hasattr(self, "master_slider"):
            SoundManager.set_volumes(
                master=self.master_slider["value"],
                sfx=self.sfx_slider["value"],
                music=self.music_slider["value"],
            )

    def _save_audio(self):
        self.config["audio"] = {
            "master_volume": self.master_slider["value"],
            "sfx_volume": self.sfx_slider["value"],
            "music_volume": self.music_slider["value"],
        }
        save_config(self.config)

    # ── EDITOR ───────────────────────────────────────────────────────────────

    def _open_editor(self):
        SoundManager.play("menu_click")
        from level_editor import LevelEditor
        self.cleanup()
        LevelEditor(self.base, self._return_to_menu)

    # ── UTILS ────────────────────────────────────────────────────────────────

    def _clear(self):
        """Remove widgets antigos."""
        for child in self.root.getChildren():
            child.removeNode()
        for attr in ["bg", "_settings_panel"]:
            if hasattr(self, attr):
                obj = getattr(self, attr)
                if obj:
                    try:
                        obj.destroy()
                    except Exception:
                        pass

    def cleanup(self):
        self._clear()
        if hasattr(self, "root"):
            self.root.removeNode()
        SoundManager.stop_music()