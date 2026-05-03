# 🎨 Paint Shooter

Jogo em primeira pessoa onde você atira blocos coloridos para pintar quadros.
Desenvolvido em Python com **Panda3D**.

---

## 📦 Instalação

```bash
pip install panda3d
```

## ▶️ Executar

```bash
cd paint_shooter
python main.py
```

---

## 🎮 Controles (padrão)

| Ação           | Tecla       |
|----------------|-------------|
| Atirar         | Espaço / Clique esquerdo |
| Girar bloco    | A / D       |
| Mover mira     | Mouse       |
| Pausar         | Escape      |

> Todos os controles podem ser remapeados em **Configurações → Controles**.

---

## 📁 Estrutura de Arquivos

```
paint_shooter/
├── main.py           # Ponto de entrada
├── game.py           # Lógica principal do gameplay
├── menu.py           # Menu principal e configurações
├── level_editor.py   # Editor de fases
├── save_manager.py   # Gerenciamento dos 3 slots de save
├── block_utils.py    # Análise de blocos conectados, rotação
├── sound_manager.py  # Gerenciador de efeitos sonoros ← EDITE AQUI
├── levels.json       # Fases do jogo ← EDITE AQUI
├── config.json       # Configurações do jogador
└── assets/
    └── sounds/       # Coloque seus arquivos de áudio aqui
```

---

## 🔊 Adicionando Sons

1. Coloque seus arquivos `.wav` ou `.ogg` em `assets/sounds/`
2. Abra `sound_manager.py`
3. Edite o dicionário `SFX_FILES`:

```python
SFX_FILES = {
    "shoot":        "meu_tiro.wav",
    "hit_correct":  "acerto.wav",
    "hit_wrong":    "erro.wav",
    "game_over":    "game_over.wav",
    "level_clear":  "vitoria.wav",
    "menu_click":   "click.wav",
    "rewind":       "rewind.wav",
    "star_earned":  "estrela.wav",
}

MUSIC_FILES = {
    "menu":         "musica_menu.ogg",
    "gameplay":     "musica_jogo.ogg",
}
```

Os pontos de chamada no código estão marcados com:
```python
SoundManager.play("nome_do_som")  # ← PONTO DE EFEITO SONORO
```

---

## 📝 Editando Fases (`levels.json`)

Cada fase tem esta estrutura:

```json
{
  "id": 1,
  "name": "Fase 1 - Cruz",
  "grid_size": [5, 5],
  "matrix": [
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0],
    [2, 2, 3, 2, 2],
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0]
  ],
  "colors": {
    "1": [1.0, 0.2, 0.2, 1.0],
    "2": [0.2, 0.5, 1.0, 1.0],
    "3": [1.0, 1.0, 0.2, 1.0]
  },
  "time_3stars": 30,
  "time_2stars": 60,
  "time_1star":  90
}
```

**Paleta de cores padrão:**

| ID | Cor      |
|----|----------|
| 1  | Vermelho |
| 2  | Azul     |
| 3  | Amarelo  |
| 4  | Verde    |
| 5  | Laranja  |
| 6  | Roxo     |
| 7  | Ciano    |
| 8  | Rosa     |
| 9  | Marrom   |
| 10 | Branco   |

Células com `0` são vazias (não precisam ser pintadas).

Células com o mesmo número **e que estejam conectadas** (adjacentes ortogonalmente) formam **um único bloco** que será atirado juntos.

---

## 💾 Saves

Os 3 saves ficam em `saves/save_0.json`, `save_1.json`, `save_2.json`.  
Cada save guarda:
- Nome do jogador
- Fase atual
- Melhor tempo e estrelas por fase
- Total de estrelas

---

## 🏆 Sistema de Estrelas

Cada fase tem 3 tempos configuráveis:

- `time_3stars` — tempo máximo para 3 estrelas (segundos)
- `time_2stars` — tempo máximo para 2 estrelas
- `time_1star`  — tempo máximo para 1 estrela

Acima de `time_1star` = 0 estrelas (mas a fase é concluída).

**Dica:** Teste cada fase e ajuste os tempos diretamente em `levels.json`.

---

## ⚙️ Mecânicas

### Quadros se aproximando
- Vários quadros vêm em fila do fundo da cena
- Velocidade base: **2.5 unidades/seg**
- Cada erro aumenta a velocidade em **+0.5**
- Se um quadro chegar muito perto sem ser pintado → **Game Over**

### Blocos
- Extraídos automaticamente da matriz por flood-fill
- Ordem de aparição aleatória
- Rotação com **A** (anti-horário) e **D** (horário)

### Preview
- **Azul** = mirando no quadro
- **Verde** = encaixe correto
- **Vermelho** = encaixe incorreto

### Animação de conclusão
- Ao completar todos os blocos, os quadros voltam ao ponto de origem
- Do fundo emerge um quadro final com a imagem completa sobreposta
