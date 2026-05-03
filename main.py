"""
main.py
Ponto de entrada do Paint Shooter.

Requisitos:
    pip install panda3d

Executar:
    python main.py
"""

import sys
import os

# Garante que o diretório do jogo está no path
sys.path.insert(0, os.path.dirname(__file__))

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    loadPrcFileData,
    WindowProperties,
    AntialiasAttrib,
    ConfigVariableBool,
    Vec4,
)
from sound_manager import SoundManager
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


class PaintShooter(ShowBase):
    """Classe principal do jogo."""

    def __init__(self):
        config = load_config()
        graphics = config.get("graphics", {})
        fullscreen = graphics.get("fullscreen", True)
        resolution = graphics.get("resolution", [1920, 1080])

        # Configurações do Panda3D antes de inicializar
        loadPrcFileData("", f"window-title Paint Shooter")
        loadPrcFileData("", f"win-size {resolution[0]} {resolution[1]}")
        loadPrcFileData("", "show-frame-rate-meter 0")
        loadPrcFileData("", "sync-video 1")
        loadPrcFileData("", "audio-library-name p3openal_audio")

        super().__init__()

        # Tela cheia
        if fullscreen:
            props = WindowProperties()
            props.setFullscreen(True)
            props.setSize(resolution[0], resolution[1])
            self.win.requestProperties(props)

        # Antialiasing
        self.render.setAntialias(AntialiasAttrib.MAuto)

        # Cor de fundo
        self.setBackgroundColor(0.03, 0.03, 0.06, 1.0)

        # Câmera padrão (primeira pessoa — câmera estática, objetos se movem)
        self.camera.setPos(0, 0, 1.7)
        self.camera.lookAt(0, 20, 1.7)
        self.camLens.setFov(75)
        self.camLens.setNear(0.1)
        self.camLens.setFar(500)

        # Desativa controle padrão de câmera
        self.disableMouse()

        # Inicializa gerenciador de sons
        audio_cfg = config.get("audio", {})
        SoundManager.init(
            self,
            master_vol=audio_cfg.get("master_volume", 1.0),
            sfx_vol=audio_cfg.get("sfx_volume", 1.0),
            music_vol=audio_cfg.get("music_volume", 0.7),
        )

        # Inicia menu principal
        self._launch_menu()

    def _launch_menu(self):
        """Abre o menu principal."""
        from menu import Menu
        self.current_screen = Menu(self)


if __name__ == "__main__":
    game = PaintShooter()
    game.run()
