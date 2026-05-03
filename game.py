"""
game.py
Lógica principal do gameplay — visão em primeira pessoa, quadros se aproximando,
mecânica de atirar blocos, preview, animação de conclusão.
"""

import json
import os
import math
import random
from panda3d.core import (
    NodePath, LVector3f, LVector4f, LPoint3f,
    CardMaker, TextNode, TransparencyAttrib,
    LineSegs, GeomNode, CollisionNode, CollisionRay,
    CollisionHandlerQueue, CollisionTraverser,
    MouseWatcher, PandaNode, Vec3,
    AmbientLight, DirectionalLight,
)
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel
from direct.interval.IntervalGlobal import (
    Sequence, Parallel, LerpPosInterval, LerpColorScaleInterval,
    LerpColorInterval, Func, Wait
)
from block_utils import (
    find_connected_blocks, blocks_to_queue,
    rotate_shape_cw, rotate_shape_ccw,
    can_place, get_shape_bounds
)
from sound_manager import SoundManager

LEVELS_PATH = os.path.join(os.path.dirname(__file__), "levels.json")

# Distância na qual o quadro causa game over
GAME_OVER_DIST = 2.0
# Distância inicial de spawn dos quadros
SPAWN_DIST = 30.0
# Espaçamento entre quadros na fila
FRAME_SPACING = 8.0
# Velocidade base dos quadros (unidades/seg)
BASE_SPEED = 2.5
# Quanto acelera ao errar
MISS_SPEED_INCREASE = 0.5
# Bônus de tempo (segundos descontados) ao acertar um bloco
HIT_TIME_BONUS = 2.0


COLOR_PALETTE = {
    1:  (1.0, 0.2, 0.2, 1.0),   # vermelho
    2:  (0.2, 0.5, 1.0, 1.0),   # azul
    3:  (1.0, 1.0, 0.2, 1.0),   # amarelo
    4:  (0.2, 0.9, 0.3, 1.0),   # verde
    5:  (0.9, 0.4, 0.1, 1.0),   # laranja
    6:  (0.7, 0.2, 0.9, 1.0),   # roxo
    7:  (0.2, 0.9, 0.9, 1.0),   # ciano
    8:  (1.0, 0.5, 0.7, 1.0),   # rosa
    9:  (0.5, 0.3, 0.1, 1.0),   # marrom
    10: (0.9, 0.9, 0.9, 1.0),   # branco
}


def load_levels() -> list[dict]:
    with open(LEVELS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class CanvasFrame:
    """
    Representa um quadro (tela) se aproximando do jogador.
    Cada quadro exibe a grade completa da fase mas pertence a UM bloco específico
    (color_id + cells). Fica completo quando esse bloco for pintado corretamente.
    """

    CELL_SIZE = 0.5

    def __init__(self, render, level_data: dict, frame_index: int,
                 z_position: float, colors: dict, block: dict):
        self.level_data   = level_data
        self.grid_rows    = level_data["grid_size"][0]
        self.grid_cols    = level_data["grid_size"][1]
        self.colors       = colors
        self.frame_index  = frame_index
        self.is_complete  = False

        # Bloco que este quadro representa
        self.block_color_id: int        = block["color_id"]
        self.block_cells: set[tuple]    = set(block["cells"])   # (row, col) absolutos
        self.block_shape: list[tuple]   = block["shape"]
        self.block_pivot_r: int         = block["pivot_row"]
        self.block_pivot_c: int         = block["pivot_col"]

        # Matriz local: apenas células deste bloco marcadas com color_id
        self.pending: set[tuple] = set(self.block_cells)  # células ainda a pintar

        self.node = render.attachNewNode(f"canvas_frame_{frame_index}")
        self.node.setPos(0, z_position, 1.5)

        self.cell_nodes: dict[tuple, NodePath] = {}
        self._preview_cells: list[tuple] = []
        self._build_grid()

    def _build_grid(self):
        """Constrói a grade: células do bloco em destaque, resto escuro."""
        cs   = self.CELL_SIZE
        rows = self.grid_rows
        cols = self.grid_cols

        full_matrix = self.level_data["matrix"]

        for r in range(rows):
            for c in range(cols):
                cm = CardMaker(f"cell_{r}_{c}")
                x = (c - cols / 2.0 + 0.5) * cs
                z = ((rows - 1 - r) - rows / 2.0 + 0.5) * cs
                cm.setFrame(x - cs/2, x + cs/2, z - cs/2, z + cs/2)
                cell_np = self.node.attachNewNode(cm.generate())
                cell_np.setTwoSided(True)
                cell_np.setTransparency(TransparencyAttrib.MAlpha)

                if (r, c) in self.block_cells:
                    # Célula deste bloco: mostra cor apagada (aguardando tinta)
                    base_col = self.colors.get(self.block_color_id, (0.5, 0.5, 0.5, 1))
                    cell_np.setColor(base_col[0]*0.35, base_col[1]*0.35, base_col[2]*0.35, 0.9)
                elif full_matrix[r][c] != 0:
                    # Célula de outro bloco: cinza médio
                    cell_np.setColor(0.2, 0.2, 0.2, 0.7)
                else:
                    # Vazio
                    cell_np.setColor(0.1, 0.1, 0.1, 0.5)

                self.cell_nodes[(r, c)] = cell_np

        # Borda do quadro
        ls = LineSegs()
        ls.setColor(0.7, 0.7, 0.7, 1.0)
        ls.setThickness(2.0)
        hw = cols * cs / 2
        hh = rows * cs / 2
        ls.moveTo(-hw, 0, -hh); ls.drawTo(hw, 0, -hh)
        ls.drawTo(hw, 0, hh);   ls.drawTo(-hw, 0, hh)
        ls.drawTo(-hw, 0, -hh)
        self.node.attachNewNode(ls.create())

    def paint_cells(self, shape: list[tuple], pivot_r: int, pivot_c: int, color_id: int) -> bool:
        """
        Tenta pintar o shape na posição pivot.
        Correto = color_id bate com o deste quadro E todas as células do shape
                  coincidem exatamente com as células pendentes deste bloco.
        Retorna True se correto.
        """
        # Calcula células absolutas que o jogador está tentando pintar
        attempted = {(pivot_r + dr, pivot_c + dc) for dr, dc in shape}

        # Acerto perfeito: attempted == pending E color_id correto
        correct = (color_id == self.block_color_id) and (attempted == self.pending)

        color = self.colors.get(color_id, (1.0, 1.0, 1.0, 1.0))
        for r, c in attempted:
            cell_np = self.cell_nodes.get((r, c))
            if cell_np:
                cell_np.setColor(*color)

        if correct:
            self.pending.clear()
            self.is_complete = True

        return correct

    def highlight_preview(self, shape: list[tuple], pivot_r: int, pivot_c: int, color_id: int):
        """Preview: verde se alinha perfeitamente, azul se parcial/errado."""
        self.clear_preview()

        attempted = {(pivot_r + dr, pivot_c + dc) for dr, dc in shape}
        aligned   = (color_id == self.block_color_id) and (attempted == self.pending)
        preview_color = (0.2, 1.0, 0.3, 0.7) if aligned else (0.2, 0.5, 1.0, 0.6)

        self._preview_cells = []
        for dr, dc in shape:
            r, c = pivot_r + dr, pivot_c + dc
            cell_np = self.cell_nodes.get((r, c))
            if cell_np:
                cell_np.setColor(*preview_color)
                self._preview_cells.append((r, c))

    def clear_preview(self):
        """Restaura cores originais das células em preview."""
        for r, c in self._preview_cells:
            cell_np = self.cell_nodes.get((r, c))
            if not cell_np:
                continue
            if (r, c) in self.block_cells:
                if (r, c) in self.pending:
                    base_col = self.colors.get(self.block_color_id, (0.5, 0.5, 0.5, 1))
                    cell_np.setColor(base_col[0]*0.35, base_col[1]*0.35, base_col[2]*0.35, 0.9)
                else:
                    color = self.colors.get(self.block_color_id, (1.0, 1.0, 1.0, 1.0))
                    cell_np.setColor(*color)
            elif self.level_data["matrix"][r][c] != 0:
                cell_np.setColor(0.2, 0.2, 0.2, 0.7)
            else:
                cell_np.setColor(0.1, 0.1, 0.1, 0.5)
        self._preview_cells = []

    def get_position(self) -> float:
        return self.node.getY()

    def move_forward(self, amount: float):
        self.node.setY(self.node.getY() - amount)

    def destroy(self):
        self.node.removeNode()


class GameState:
    """Estados possíveis do jogo."""
    PLAYING = "playing"
    PAUSED = "paused"
    REWIND = "rewind"
    LEVEL_COMPLETE = "level_complete"
    GAME_OVER = "game_over"


class Game:
    """Controlador principal do gameplay."""

    def __init__(self, base, level_id: int, save_slot: int, on_exit_callback):
        self.base = base
        self.level_id = level_id
        self.save_slot = save_slot
        self.on_exit = on_exit_callback
        self.state = GameState.PLAYING

        self.levels = load_levels()
        self.level_data = next((l for l in self.levels if l["id"] == level_id), self.levels[0])

        # Cores da fase
        raw_colors = self.level_data.get("colors", {})
        self.colors = {int(k): tuple(v) for k, v in raw_colors.items()}
        # Fallback para paleta padrão
        for cid, col in COLOR_PALETTE.items():
            if cid not in self.colors:
                self.colors[cid] = col

        # Extrai blocos da matriz
        blocks = find_connected_blocks(self.level_data["matrix"])
        self.block_queue = blocks_to_queue(blocks, shuffle=True)
        self.current_block_idx = 0
        self.current_shape = list(self.block_queue[0]["shape"]) if self.block_queue else []
        self.current_color_id = self.block_queue[0]["color_id"] if self.block_queue else 0

        # Quadros na cena
        self.frames: list[CanvasFrame] = []
        self.frame_speed = BASE_SPEED
        self.total_frames = len(self.block_queue)

        # Estado da mira
        self.aim_frame_idx: int = 0        # índice do quadro sendo mirado
        self.aim_pivot_r: int = 0
        self.aim_pivot_c: int = 0

        # Tempo
        self.elapsed_time: float = 0.0
        self.running = True

        # Setup cena
        self.render_node = base.render.attachNewNode("game_root")
        self._setup_lights()
        self._setup_frames()
        self._setup_hud()
        self._setup_gun()
        self._setup_input()

        # Task de update
        self.update_task = base.taskMgr.add(self.update, "game_update")

        # Esconde cursor e captura mouse
        base.win.requestProperties(base.win.getProperties())

        SoundManager.play_music("gameplay")

    # ── SETUP ────────────────────────────────────────────────────────────────

    def _setup_lights(self):
        ambient = AmbientLight("ambient")
        ambient.setColor((0.4, 0.4, 0.4, 1))
        self.render_node.setLight(self.render_node.attachNewNode(ambient))

        sun = DirectionalLight("sun")
        sun.setColor((0.9, 0.9, 0.8, 1))
        sun_np = self.render_node.attachNewNode(sun)
        sun_np.setHpr(45, -45, 0)
        self.render_node.setLight(sun_np)

    def _setup_frames(self):
        """Cria os quadros na fila — cada um representa um bloco específico."""
        for i, block in enumerate(self.block_queue):
            y = SPAWN_DIST + i * FRAME_SPACING
            frame = CanvasFrame(
                self.render_node, self.level_data, i, y, self.colors, block
            )
            self.frames.append(frame)

    def _setup_gun(self):
        """Cria a representação visual da arma na tela."""
        cm = CardMaker("gun")
        cm.setFrame(-0.15, 0.15, -0.4, 0.1)
        self.gun_np = self.base.aspect2d.attachNewNode(cm.generate())
        self.gun_np.setColor(0.3, 0.3, 0.3, 1.0)
        self.gun_np.setPos(0, 0, -0.7)

        # Preview do bloco atual na arma
        self._build_block_preview_hud()

    def _build_block_preview_hud(self):
        """Mostra o bloco atual que o jogador vai atirar."""
        if hasattr(self, "block_preview_np") and self.block_preview_np:
            self.block_preview_np.removeNode()

        self.block_preview_np = self.base.aspect2d.attachNewNode("block_preview")
        self.block_preview_np.setPos(-1.5, 0, -0.5)

        if self.current_block_idx >= len(self.block_queue):
            return

        block = self.block_queue[self.current_block_idx]
        color = self.colors.get(self.current_color_id, (1.0, 1.0, 1.0, 1.0))
        cs = 0.08

        for dr, dc in self.current_shape:
            cm = CardMaker(f"prev_{dr}_{dc}")
            x = dc * cs
            z = -dr * cs
            cm.setFrame(x, x + cs, z, z + cs)
            cell = self.block_preview_np.attachNewNode(cm.generate())
            cell.setColor(*color)
            cell.setTwoSided(True)

        # Label "PRÓXIMO"
        txt = OnscreenText(
            text="BLOCO ATUAL",
            pos=(-1.5, -0.42),
            scale=0.04,
            fg=(1, 1, 1, 0.8),
            parent=self.base.aspect2d,
            mayChange=False,
        )
        if not hasattr(self, "_hud_texts"):
            self._hud_texts = []
        self._hud_texts.append(txt)

    def _setup_hud(self):
        """Cria o HUD: timer, blocos restantes, mira."""
        self._hud_texts = []

        self.hud_timer = OnscreenText(
            text="00:00", pos=(0, 0.9), scale=0.07,
            fg=(1, 1, 1, 1), shadow=(0, 0, 0, 0.5),
            parent=self.base.aspect2d,
        )

        self.hud_blocks = OnscreenText(
            text=f"Blocos: {self.total_frames}", pos=(1.2, 0.9), scale=0.055,
            fg=(1, 1, 0.2, 1), shadow=(0, 0, 0, 0.5),
            parent=self.base.aspect2d,
        )

        # Mira central
        self.crosshair = OnscreenText(
            text="+", pos=(0, 0), scale=0.06,
            fg=(1, 1, 1, 0.9),
            parent=self.base.aspect2d,
        )

    def _setup_input(self):
        """Registra inputs do teclado e mouse."""
        from panda3d.core import loadPrcFileData
        cfg = self._load_config()
        kb = cfg.get("keybindings", {})

        shoot_key = kb.get("shoot", "space")
        rot_l = kb.get("rotate_left", "a")
        rot_r = kb.get("rotate_right", "d")

        self.base.accept(shoot_key, self._shoot)
        self.base.accept("mouse1", self._shoot)
        self.base.accept(rot_l, self._rotate_ccw)
        self.base.accept(rot_r, self._rotate_cw)
        self.base.accept("escape", self._toggle_pause)

    def _load_config(self) -> dict:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    # ── UPDATE ───────────────────────────────────────────────────────────────

    def update(self, task):
        if self.state != GameState.PLAYING:
            return task.cont

        dt = globalClock.getDt()
        self.elapsed_time += dt

        # Atualiza timer
        mins = int(self.elapsed_time) // 60
        secs = int(self.elapsed_time) % 60
        self.hud_timer.setText(f"{mins:02d}:{secs:02d}")

        # Move quadros
        for frame in self.frames:
            frame.move_forward(self.frame_speed * dt)

            # Verifica game over
            if frame.get_position() <= GAME_OVER_DIST and not frame.is_complete:
                self._game_over()
                return task.cont

        # Atualiza mira / preview
        self._update_aim()

        return task.cont

    def _update_aim(self):
        """
        Calcula qual célula o jogador está mirando no quadro alvo atual.
        O quadro alvo é sempre frames[current_block_idx] — o bloco da vez.
        Usa ray casting real contra o plano Y do quadro.
        """
        if not self.base.mouseWatcherNode.hasMouse():
            return
        if self.current_block_idx >= len(self.frames):
            return

        target_frame = self.frames[self.current_block_idx]
        if target_frame.is_complete:
            return

        # Limpa preview de todos os frames
        for f in self.frames:
            if f._preview_cells:
                f.clear_preview()

        # ── Ray casting ──────────────────────────────────────────────────────
        mx = self.base.mouseWatcherNode.getMouseX()
        my = self.base.mouseWatcherNode.getMouseY()

        lens   = self.base.camLens
        cam_np = self.base.camera

        p_near = LPoint3f()
        p_far  = LPoint3f()
        lens.extrude((mx, my), p_near, p_far)

        near_world = self.base.render.getRelativePoint(cam_np, p_near)
        far_world  = self.base.render.getRelativePoint(cam_np, p_far)

        ray_dir = far_world - near_world
        if abs(ray_dir.y) < 1e-6:
            return

        plane_y = target_frame.get_position()
        t = (plane_y - near_world.y) / ray_dir.y
        if t < 0:
            return

        hit_x = near_world.x + t * ray_dir.x
        hit_z = near_world.z + t * ray_dir.z

        local_x = hit_x - target_frame.node.getX()
        local_z = hit_z - target_frame.node.getZ()

        cs   = CanvasFrame.CELL_SIZE
        rows = target_frame.grid_rows
        cols = target_frame.grid_cols

        col_f = local_x / cs + cols / 2.0 - 0.5
        row_f = -local_z / cs + rows / 2.0 - 0.5

        self.aim_frame_idx = self.current_block_idx
        self.aim_pivot_r   = int(round(row_f))
        self.aim_pivot_c   = int(round(col_f))

        target_frame.highlight_preview(
            self.current_shape, self.aim_pivot_r, self.aim_pivot_c, self.current_color_id
        )

    # ── AÇÕES ────────────────────────────────────────────────────────────────

    def _shoot(self):
        """Atira o bloco atual no quadro alvo."""
        if self.state != GameState.PLAYING:
            return
        if self.current_block_idx >= len(self.block_queue):
            return

        SoundManager.play("shoot")  # ← PONTO DE EFEITO SONORO

        frame = self.frames[self.current_block_idx] if self.current_block_idx < len(self.frames) else None
        if frame is None or frame.is_complete:
            return

        correct = frame.paint_cells(
            self.current_shape, self.aim_pivot_r, self.aim_pivot_c, self.current_color_id
        )

        if correct:
            SoundManager.play("hit_correct")  # ← PONTO DE EFEITO SONORO
            # Desconta tempo como bônus
            self.elapsed_time = max(0.0, self.elapsed_time - HIT_TIME_BONUS)
            # Quadro pintado: sobe
            self._slide_frame_away(frame)

            # Avança para o próximo bloco
            self.current_block_idx += 1
            self.hud_blocks.setText(f"Blocos: {self.total_frames - self.current_block_idx}")

            if self.current_block_idx < len(self.block_queue):
                self.current_shape    = list(self.block_queue[self.current_block_idx]["shape"])
                self.current_color_id = self.block_queue[self.current_block_idx]["color_id"]
                self._build_block_preview_hud()
            else:
                # Último bloco acertado — aguarda slide e inicia rewind
                self.base.taskMgr.doMethodLater(
                    0.9, lambda t: self._start_completion_animation(), "delay_rewind"
                )
        else:
            SoundManager.play("hit_wrong")    # ← PONTO DE EFEITO SONORO
            self.frame_speed += MISS_SPEED_INCREASE  # penalidade: acelera
            # Bloco NÃO avança — jogador tenta de novo no mesmo quadro

    def _slide_frame_away(self, frame):
        """Anima o quadro subindo para fora de cena ao ser completado com acerto."""
        current_pos = frame.node.getPos()
        target_pos = LPoint3f(current_pos.x, current_pos.y, current_pos.z + 14)
        # Guarda posição original para a animação de rewind
        frame.original_pos = current_pos
        anim = LerpPosInterval(
            frame.node, duration=0.65,
            pos=target_pos,
            startPos=current_pos,
            blendType="easeIn",
        )
        fade = LerpColorScaleInterval(frame.node, 0.65, (1, 1, 1, 0), (1, 1, 1, 1))
        Parallel(anim, fade).start()

    def _rotate_cw(self):
        """Rotaciona o bloco atual no sentido horário."""
        if self.state != GameState.PLAYING:
            return
        self.current_shape = rotate_shape_cw(self.current_shape)

    def _rotate_ccw(self):
        """Rotaciona o bloco atual no sentido anti-horário."""
        if self.state != GameState.PLAYING:
            return
        self.current_shape = rotate_shape_ccw(self.current_shape)

    def _toggle_pause(self):
        if self.state == GameState.PLAYING:
            self.state = GameState.PAUSED
            self._show_pause_menu()
        elif self.state == GameState.PAUSED:
            self.state = GameState.PLAYING
            self._hide_pause_menu()

    # ── ANIMAÇÃO DE CONCLUSÃO ────────────────────────────────────────────────

    def _start_completion_animation(self):
        """
        Animação de rewind em 3 etapas:
        1. Quadros descem do alto em sequência, ficando espaçados verticalmente.
        2. Todos se comprimem para o centro (empilham).
        3. Quadros somem e surge o quadro final fundido.
        """
        self.state = GameState.REWIND
        self.base.taskMgr.remove("game_update")
        SoundManager.play("rewind")  # ← PONTO DE EFEITO SONORO

        CENTER_Y  = 9.0    # profundidade do ponto de convergência
        CENTER_Z  = 1.5    # altura central
        SPREAD    = 1.2    # espaçamento vertical entre quadros ao descer
        DROP_DUR  = 0.50   # duração da descida de cada quadro
        DELAY_IN  = 0.13   # delay escalonado entre cada quadro

        n = len(self.frames)
        # Posições Z espaçadas simétricas ao redor de CENTER_Z
        spread_zs = [CENTER_Z + (i - (n - 1) / 2.0) * SPREAD for i in range(n)]

        # Etapa 1: descem do alto para posições espaçadas, depois
        # Etapa 2: comprimem para CENTER_Z
        # Construída como sequência por frame para garantir que o push
        # usa a posição já definida, não a posição antes do drop.

        def make_frame_seq(f, target_z, drop_delay):
            sp = LPoint3f(0, CENTER_Y, CENTER_Z + 22)
            tp = LPoint3f(0, CENTER_Y, target_z)
            cp = LPoint3f(0, CENTER_Y, CENTER_Z)
            return Sequence(
                # Drop
                Wait(drop_delay),
                Func(f.node.setPos, sp),
                Func(f.node.show),
                Func(lambda nd=f.node: nd.setColorScale(1, 1, 1, 0)),
                Parallel(
                    LerpPosInterval(f.node, DROP_DUR, tp, startPos=sp, blendType="easeOut"),
                    LerpColorScaleInterval(f.node, DROP_DUR * 0.8, (1, 1, 1, 0.88), (1, 1, 1, 0)),
                ),
                # Pausa breve após cada um chegar
                Wait(0.08),
            )

        drop_seqs = [
            make_frame_seq(frame, spread_zs[i], i * DELAY_IN)
            for i, frame in enumerate(self.frames)
        ]

        # Duração total da fase de drop
        drop_total = n * DELAY_IN + DROP_DUR + 0.08 * n

        # Fase de push: todos vão para CENTER_Z simultaneamente
        def start_push():
            push_seqs = [
                LerpPosInterval(frame.node, 0.5,
                                LPoint3f(0, CENTER_Y, CENTER_Z),
                                blendType="easeInOut")
                for frame in self.frames
            ]
            Sequence(
                Parallel(*push_seqs),
                Wait(0.25),
                Func(self._merge_into_final_canvas),
            ).start()

        Sequence(
            Parallel(*drop_seqs),
            Wait(0.3),
            Func(start_push),
        ).start()

    def _merge_into_final_canvas(self):
        """Esconde quadros individuais e exibe quadro final fundido."""
        for frame in self.frames:
            frame.node.hide()

        CENTER_Y = 9.0
        CENTER_Z = 1.5

        matrix = self.level_data["matrix"]
        rows   = self.level_data["grid_size"][0]
        cols   = self.level_data["grid_size"][1]
        cs     = CanvasFrame.CELL_SIZE

        final_np = self.render_node.attachNewNode("final_canvas")
        final_np.setPos(0, CENTER_Y + 1.5, CENTER_Z)
        final_np.setColorScale(1, 1, 1, 0)

        for r in range(rows):
            for c in range(cols):
                val = matrix[r][c]
                color = self.colors.get(val, (0.18, 0.18, 0.18, 1.0)) if val != 0 \
                        else (0.08, 0.08, 0.08, 0.5)
                cm = CardMaker(f"fc_{r}_{c}")
                x = (c - cols / 2.0 + 0.5) * cs
                z = ((rows - 1 - r) - rows / 2.0 + 0.5) * cs
                cm.setFrame(x - cs/2, x + cs/2, z - cs/2, z + cs/2)
                cell = final_np.attachNewNode(cm.generate())
                cell.setColor(*color)
                cell.setTwoSided(True)
                cell.setTransparency(TransparencyAttrib.MAlpha)

        # Borda dourada
        ls = LineSegs()
        ls.setColor(1.0, 0.88, 0.2, 1.0)
        ls.setThickness(3.0)
        hw = cols * cs / 2; hh = rows * cs / 2
        ls.moveTo(-hw, 0, -hh); ls.drawTo(hw, 0, -hh)
        ls.drawTo(hw, 0, hh);   ls.drawTo(-hw, 0, hh)
        ls.drawTo(-hw, 0, -hh)
        final_np.attachNewNode(ls.create())

        # Surge vindo de trás com fade
        Sequence(
            Parallel(
                LerpColorScaleInterval(final_np, 0.8, (1, 1, 1, 1), (1, 1, 1, 0)),
                LerpPosInterval(final_np, 0.8,
                                LPoint3f(0, CENTER_Y - 0.5, CENTER_Z),
                                startPos=LPoint3f(0, CENTER_Y + 1.5, CENTER_Z),
                                blendType="easeOut"),
            ),
            Wait(0.3),
            Func(self._show_level_complete),
        ).start()

        SoundManager.play("level_clear")  # ← PONTO DE EFEITO SONORO

    def _show_level_complete(self):
        """Exibe tela de conclusão com estrelas e opções de navegação."""
        self.state = GameState.LEVEL_COMPLETE

        stars = self._calculate_stars()
        SoundManager.play("star_earned")  # ← PONTO DE EFEITO SONORO

        import save_manager as sm
        sm.update_level_progress(self.save_slot, self.level_id, stars, self.elapsed_time)

        # Descobre se há próxima fase
        levels = load_levels()
        next_level = next((l for l in levels if l["id"] > self.level_id), None)

        self._completion_frame = DirectFrame(
            frameColor=(0, 0, 0, 0.75),
            frameSize=(-0.85, 0.85, -0.6, 0.55),
            pos=(0, 0, 0),
            parent=self.base.aspect2d,
        )

        DirectLabel(
            text="FASE COMPLETA!",
            scale=0.1, pos=(0, 0, 0.38),
            text_fg=(1, 1, 0.2, 1), frameColor=(0, 0, 0, 0),
            parent=self._completion_frame,
        )

        star_str = "★" * stars + "☆" * (3 - stars)
        DirectLabel(
            text=star_str, scale=0.15, pos=(0, 0, 0.2),
            text_fg=(1, 0.85, 0.1, 1), frameColor=(0, 0, 0, 0),
            parent=self._completion_frame,
        )

        mins = int(self.elapsed_time) // 60
        secs = int(self.elapsed_time) % 60
        DirectLabel(
            text=f"Tempo: {mins:02d}:{secs:02d}",
            scale=0.065, pos=(0, 0, 0.04),
            text_fg=(0.85, 0.85, 0.85, 1), frameColor=(0, 0, 0, 0),
            parent=self._completion_frame,
        )

        btn_y = -0.13
        if next_level:
            DirectButton(
                text=f"Próxima Fase  ▶",
                scale=0.075, pos=(0, 0, btn_y),
                text_fg=(0.2, 1.0, 0.4, 1),
                command=self._go_next_level,
                extraArgs=[next_level["id"]],
                parent=self._completion_frame,
            )
            btn_y -= 0.16

        DirectButton(
            text="Jogar Novamente",
            scale=0.07, pos=(0, 0, btn_y),
            command=self._retry,
            parent=self._completion_frame,
        )
        btn_y -= 0.16

        DirectButton(
            text="Menu Principal",
            scale=0.07, pos=(0, 0, btn_y),
            command=self._exit_to_menu,
            parent=self._completion_frame,
        )

    def _go_next_level(self, next_level_id: int):
        """Vai para a próxima fase."""
        self.cleanup()
        Game(self.base, next_level_id, self.save_slot, self.on_exit)

    def _calculate_stars(self) -> int:
        t = self.elapsed_time
        if t <= self.level_data["time_3stars"]:
            return 3
        elif t <= self.level_data["time_2stars"]:
            return 2
        elif t <= self.level_data["time_1star"]:
            return 1
        return 0

    # ── GAME OVER ────────────────────────────────────────────────────────────

    def _game_over(self):
        self.state = GameState.GAME_OVER
        self.base.taskMgr.remove("game_update")
        SoundManager.play("game_over")  # ← PONTO DE EFEITO SONORO

        self._go_frame = DirectFrame(
            frameColor=(0.5, 0, 0, 0.8),
            frameSize=(-0.7, 0.7, -0.4, 0.4),
            parent=self.base.aspect2d,
        )
        DirectLabel(
            text="GAME OVER",
            scale=0.12,
            pos=(0, 0, 0.15),
            text_fg=(1, 0.2, 0.2, 1),
            frameColor=(0, 0, 0, 0),
            parent=self._go_frame,
        )
        DirectButton(
            text="Tentar Novamente",
            scale=0.07,
            pos=(0, 0, -0.05),
            command=self._retry,
            parent=self._go_frame,
        )
        DirectButton(
            text="Menu Principal",
            scale=0.07,
            pos=(0, 0, -0.2),
            command=self._exit_to_menu,
            parent=self._go_frame,
        )

    def _retry(self):
        self.cleanup()
        new_game = Game(self.base, self.level_id, self.save_slot, self.on_exit)

    # ── PAUSA ────────────────────────────────────────────────────────────────

    def _show_pause_menu(self):
        self._pause_frame = DirectFrame(
            frameColor=(0, 0, 0, 0.7),
            frameSize=(-0.5, 0.5, -0.4, 0.4),
            parent=self.base.aspect2d,
        )
        DirectLabel(
            text="PAUSADO", scale=0.1, pos=(0, 0, 0.25),
            text_fg=(1, 1, 1, 1), frameColor=(0, 0, 0, 0),
            parent=self._pause_frame,
        )
        DirectButton(
            text="Continuar", scale=0.07, pos=(0, 0, 0.05),
            command=self._toggle_pause,
            parent=self._pause_frame,
        )
        DirectButton(
            text="Menu Principal", scale=0.07, pos=(0, 0, -0.15),
            command=self._exit_to_menu,
            parent=self._pause_frame,
        )

    def _hide_pause_menu(self):
        if hasattr(self, "_pause_frame"):
            self._pause_frame.destroy()

    # ── SAÍDA ────────────────────────────────────────────────────────────────

    def _exit_to_menu(self):
        self.cleanup()
        self.on_exit()

    def cleanup(self):
        """Remove todos os elementos da cena."""
        self.base.taskMgr.remove("game_update")
        self.base.ignoreAll()

        for frame in self.frames:
            frame.destroy()
        self.frames.clear()

        if hasattr(self, "render_node"):
            self.render_node.removeNode()
        if hasattr(self, "gun_np"):
            self.gun_np.removeNode()
        if hasattr(self, "crosshair"):
            self.crosshair.destroy()
        if hasattr(self, "hud_timer"):
            self.hud_timer.destroy()
        if hasattr(self, "hud_blocks"):
            self.hud_blocks.destroy()
        if hasattr(self, "block_preview_np"):
            self.block_preview_np.removeNode()
        for txt in getattr(self, "_hud_texts", []):
            txt.destroy()
        for attr in ["_completion_frame", "_go_frame", "_pause_frame"]:
            if hasattr(self, attr):
                getattr(self, attr).destroy()

        SoundManager.stop_music()