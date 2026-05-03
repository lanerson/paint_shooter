"""
sound_manager.py
Gerenciador de efeitos sonoros e música.

COMO ADICIONAR SONS:
1. Coloque seus arquivos de áudio na pasta  paint_shooter/assets/sounds/
2. Adicione o caminho no dicionário SFX_FILES abaixo
3. Chame SoundManager.play("nome_do_som") no momento desejado

Formatos suportados pelo Panda3D: .wav, .ogg, .mp3
"""

import os
from panda3d.core import AudioManager

# ── CONFIGURE SEUS SONS AQUI ─────────────────────────────────────────────────
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "sounds")

SFX_FILES: dict[str, str] = {
    # "nome":       "arquivo.wav",
    "shoot":        "meu_tiro.mp3",        # disparo de bloco
    "hit_correct":  "hit_correct.wav",  # bloco encaixou corretamente
    "hit_wrong":    "erro.mp3",    # bloco errou / acelerou quadro
    "game_over":    "game_over.wav",    # fim de jogo
    "level_clear":  "level_clear.wav",  # fase concluída
    "menu_click":   "click.mp3",   # clique no menu
    "countdown":    "countdown.wav",    # tick de contagem regressiva
    "rewind":       "rewind.wav",       # animação de retrocesso
    "star_earned":  "star_earned.wav",  # ganhou estrela
}

MUSIC_FILES: dict[str, str] = {
    # "nome":       "arquivo.ogg",
    "menu":         "menu.mp3",
    "gameplay":     "gameplay.mp3",
    "editor":       "music_editor.ogg",
}
# ─────────────────────────────────────────────────────────────────────────────


class SoundManager:
    """Singleton simples de gerenciamento de áudio."""

    _sfx: dict = {}
    _music: dict = {}
    _current_music = None
    _base = None
    _master_vol: float = 1.0
    _sfx_vol: float = 1.0
    _music_vol: float = 0.7

    @classmethod
    def init(cls, base, master_vol=1.0, sfx_vol=1.0, music_vol=0.7) -> None:
        """Inicializa o gerenciador. Chame uma vez na inicialização do jogo."""
        cls._base = base
        cls._master_vol = master_vol
        cls._sfx_vol = sfx_vol
        cls._music_vol = music_vol
        cls._load_all()

    @classmethod
    def _load_all(cls) -> None:
        """Carrega todos os arquivos de áudio configurados."""
        for name, filename in SFX_FILES.items():
            path = os.path.join(ASSETS_DIR, filename)
            if os.path.exists(path):
                try:
                    sound = cls._base.loader.loadSfx(path)
                    cls._sfx[name] = sound
                except Exception as e:
                    print(f"[SoundManager] Não foi possível carregar SFX '{name}': {e}")
            else:
                pass  # Arquivo não encontrado — silencioso em produção

        for name, filename in MUSIC_FILES.items():
            path = os.path.join(ASSETS_DIR, filename)
            if os.path.exists(path):
                try:
                    music = cls._base.loader.loadMusic(path)
                    cls._music[name] = music
                except Exception as e:
                    print(f"[SoundManager] Não foi possível carregar música '{name}': {e}")

    @classmethod
    def play(cls, name: str, volume: float = 1.0, loop: bool = False) -> None:
        """Toca um efeito sonoro pelo nome."""
        sfx = cls._sfx.get(name)
        if sfx:
            sfx.setVolume(volume * cls._sfx_vol * cls._master_vol)
            sfx.setLoop(loop)
            sfx.play()

    @classmethod
    def stop(cls, name: str) -> None:
        """Para um efeito sonoro."""
        sfx = cls._sfx.get(name)
        if sfx:
            sfx.stop()

    @classmethod
    def play_music(cls, name: str, loop: bool = True) -> None:
        """Toca uma música de fundo."""
        if cls._current_music:
            cls._current_music.stop()
        music = cls._music.get(name)
        if music:
            music.setVolume(cls._music_vol * cls._master_vol)
            music.setLoop(loop)
            music.play()
            cls._current_music = music

    @classmethod
    def stop_music(cls) -> None:
        """Para a música atual."""
        if cls._current_music:
            cls._current_music.stop()
            cls._current_music = None

    @classmethod
    def set_volumes(cls, master=None, sfx=None, music=None) -> None:
        """Atualiza volumes em tempo real."""
        if master is not None:
            cls._master_vol = master
        if sfx is not None:
            cls._sfx_vol = sfx
        if music is not None:
            cls._music_vol = music
        if cls._current_music:
            cls._current_music.setVolume(cls._music_vol * cls._master_vol)
