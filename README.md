# Ludo Duel

A two-player game of Ludo where you race a computer opponent that plans every move with **expectiminimax search**, taking both its own choices and the roll of the die into account.

**Play it in your browser:** https://selvarajsakthivel.itch.io/ludo-duel

| | |
|---|---|
| **Author** | Selvaraj Sakthivel (Student ID 3607YZMI) |
| **Module** | 5FTC2067 Artificial Intelligence Principles, Mini Project |
| **Language** | Python 3 (desktop game), JavaScript (web version) |

---

## The game

You play **red** and the computer plays **blue**. Each player has two tokens.

1. **Roll** the die (Space, or click your die).
2. **Choose** which token to move (press 1 or 2, or click a glowing token).
3. The token **hops** forward by the number rolled around the shared 52-square ring.
4. **Capture:** land on a normal square holding an opponent's token and it goes back to its yard.
5. **Win:** the first player to bring both tokens into the centre wins.

The two START squares and the six star squares are **safe**: tokens on them cannot be captured.

To keep the search fast, the rules are simplified: no 6 is needed to leave the yard, a 6 gives no extra turn, and a roll that overshoots the centre stops on it.

### Controls (desktop)

| Key | Action |
|---|---|
| Space / Enter | Roll the die, play again |
| 1 / 2 | Choose token 1 or token 2 |
| N | New game |
| M | Sound on / off |

The start page asks for Player 1's name, which then appears in the scores, the status line and the game log.

---

## How the computer opponent thinks

Ludo mixes **luck** (the die) with **choice** (which token to move), so plain minimax is not enough. The computer uses **expectiminimax**, which has three kinds of node:

| Node | Whose turn | Value |
|---|---|---|
| **MAX** | the computer chooses a token | the **largest** value of its moves |
| **MIN** | the human chooses a token | the **smallest** value (assumes the best reply) |
| **CHANCE** | the die is rolled | the **average** over the six faces |

At the search limit, `evaluate()` scores the position for the computer:

```
score = (my progress − opponent's progress)
      + (my tokens on safe squares − opponent's)
      + threat          (progress at risk of capture on the next roll, divided by 6)
```

A win scores +1000 and a loss −1000.

### Difficulty levels

| Level | Looks ahead | Notes |
|---|---|---|
| Easy | 1 move | plays a random token 40% of the time |
| Medium | 2 moves | |
| Hard | 4 moves | about 14 ms per move |

The **AI Thinking** tab in the game shows the value the computer computed for each token on every turn.

---

## Results

`experiments.py` plays 400 games per match-up, swapping seats and who moves first.

| Match-up | Computer win rate |
|---|---|
| Depth 1 vs random player | 70.5% |
| Depth 2 vs random player | 70.8% |
| Depth 3 vs random player | 71.5% |
| Depth 4 vs random player | 77.8% |
| Progress-only evaluation vs random | 57.5% |
| Full evaluation vs random | 70.2% |

The evaluation terms matter more than search depth, because with two tokens the die decides much of the game.

---

## Run it

**Desktop game (Python 3)**

```bash
pip install -r requirements.txt     # Pillow, NumPy
python ludo_main_gui.py
```

Or open the folder in PyCharm and run `ludo_main_gui.py`.

**Web game:** open `web/index.html` in any browser (computer or phone). It is a single self-contained file with its pictures and sounds inside.

**Tests and experiments**

```bash
python ludo_logic.py     # plays 1,000 random games and checks the rules
python experiments.py    # measures the computer opponent
```

---

## Project structure

| File | Purpose |
|---|---|
| `ludo_logic.py` | Rules: game state, legal moves, capture, winner |
| `ai.py` | Expectiminimax search, `evaluate()`, random player |
| `ludo_main_gui.py` | Desktop game window (Tkinter): start page, turns, animation |
| `ui_art.py`, `ui_dice.py`, `ui_kit.py` | Drawing the board, pawns and 3-D dice (Pillow, NumPy) |
| `ui_start.py` | Start page with the name box |
| `ui_sound.py` | Sound effects |
| `experiments.py` | Plays many games to measure the computer opponent |
| `web/index.html` | Web version of the same rules and opponent (JavaScript) |
| `fonts/`, `sounds/` | Fonts and sound effects used by the game |

The rules know nothing about the screen or the computer opponent, so each part can be tested on its own.

---

## Credits

- Sound effects: [Kenney](https://kenney.nl) (CC0)
- Fonts: Poppins and Lilita One (SIL Open Font License, see `fonts/`)
