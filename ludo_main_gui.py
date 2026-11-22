# Name:       SELVARAJ SAKTHIVEL
# Student ID: 3607YZMI
# Module:     5FTC2067 Artificial Intelligence Principles - Mini Project
# File:       ludo_main_gui.py
# Game:       Ludo Duel - the desktop game window (Tkinter)
#
# RUN:  open this file in PyCharm and press the green Run button, or use
#       python ludo_main_gui.py
#
# You play RED (top-right yard), the computer plays BLUE (bottom-left yard).
# The rules come from ludo_logic.py and the computer player (expectiminimax)
# from ai.py; the web version (web/index.html) is a port of the same two.
# Every picture is painted by ui_art.py (Pillow + NumPy); this file puts them
# on one Tkinter canvas and runs the game. Pillow and NumPy must be installed
# (pip install -r requirements.txt).
#
# ORGANISATION  1. constants   2. helpers (calculations only)
#               3. LudoApp (window, input, animation, game flow)   4. main()
# ANIMATION     Every move is a small "script": a Python generator that moves
#               things a little and then does `yield` to hand control back to
#               Tkinter, which wakes it again about 60 times a second. So a
#               script reads like a story: roll the die, hop square by square,
#               explode, fly home, ...

import math
import os
import random
import time
import tkinter as tk
from collections import namedtuple

try:
    from PIL import ImageTk
    import ui_art
    import ui_start
    from ui_sound import SoundPlayer
    from ui_dice import resting_rotation, rot_axis
except ImportError as error:                  # Pillow or NumPy is missing
    raise SystemExit(f"[Ludo Duel] {error}. Install the requirements with:  "
                     "pip install -r requirements.txt")

from ludo_logic import (new_game, roll_dice, get_legal_moves, destination,
                        is_capture, apply_move, get_winner, ring_square,
                        START, FINISH, HOME_COLUMN_FIRST, SAFE_RING_SQUARES,
                        TOKENS_PER_PLAYER)
from ai import choose_best_move

# Shown in the window (spec: name + ID in every component).
STUDENT_NAME = "SELVARAJ SAKTHIVEL"
STUDENT_ID = "3607YZMI"
STUDENT = (STUDENT_NAME, STUDENT_ID, "5FTC2067", "AI Principles Mini Project")
NAME_HINT = "Enter your name"

HUMAN = 0   # player index of the person at the keyboard (red tokens)
AI = 1      # player index of the computer (blue tokens)

# For each difficulty: (search depth in moves, chance of a random "mistake").
# These are the same settings as the web version.
DIFFICULTY = {
    "Easy": (1, 0.4),     # looks 1 move ahead and blunders 40% of the time
    "Medium": (2, 0.0),   # also considers your reply
    "Hard": (4, 0.0),     # looks two full rounds ahead
}

# How fast the animations run: the label on the button and its speed factor.
SPEEDS = {"Normal": 1.0, "Fast": 2.5}

# Colours of the texts in the status card, and of the window behind the
# pictures (only visible for a moment while the window is being resized).
BACKGROUND = "#050c20"
HUMAN_INK = ui_art.GOLD                    # your messages
AI_INK = ui_art.SIDE[AI]["text"]           # the computer's messages
CONFETTI_COLOURS = ("#e82426", "#1c6cf0", "#ffbe04", "#34d399", "#f472b6",
                    "#ffffff")

# Where text goes on the status card and the scoreboard, in design units (x1,
# y1, x2, y2). The card frames themselves are painted by ui_art.py.
STATUS_TITLE_BOX = (872.0, 288.0, 1250.0, 328.0)
STATUS_SUB_BOX = (872.0, 326.0, 1250.0, 348.0)
SCORE_BOX = {HUMAN: (978.0, 456.0, 1010.0, 504.0),
             AI: (1222.0, 456.0, 1254.0, 504.0)}
HOME_TEXT_BOX = {HUMAN: (884.0, 500.0, 1020.0, 526.0),
                 AI: (1131.0, 500.0, 1260.0, 526.0)}

# How tokens sharing one square are arranged: for 1, 2, 3 or 4 tokens a
# list of (shift right, shift down, scale) per token.
STACK_LAYOUTS = {
    1: ((0.0, 0.0, 1.0),),
    2: ((-0.23, 0.0, 0.78), (0.23, 0.0, 0.78)),
    3: ((-0.23, -0.2, 0.62), (0.23, -0.2, 0.62), (0.0, 0.24, 0.62)),
    4: ((-0.23, -0.23, 0.6), (0.23, -0.23, 0.6),
        (-0.23, 0.23, 0.6), (0.23, 0.23, 0.6)),
}

# Where one token stands: x and y are the CENTRE of the token, counted in
# squares from the top-left corner of the board; scale shrinks or grows the
# token (1.0 = alone on a square of the track).
Slot = namedtuple("Slot", ["x", "y", "scale"])

YARD_SCALE = 1.35          # tokens waiting in the yard are drawn bigger
CENTRE_SCALE = 0.75        # tokens that reached the centre are smaller
WARM_SCALES = (YARD_SCALE, 1.0, 0.78, CENTRE_SCALE, 0.62, 0.6)

# ----- Animation times, in seconds (the "Fast" button divides them). -----
FRAME_MS = 15              # a new picture about every 15 ms
HOP_SECONDS = 0.22         # one hop = one square
REST_SECONDS = 0.04        # short rest on a square before the next hop
FLY_SECONDS = 0.55         # a captured token flies back to its yard
SETTLE_SECONDS = 0.2       # tokens sharing a square move aside
LEAD_SECONDS = 0.12        # pause before anything moves
GAP_SECONDS = 0.35         # pause between your move and the AI's turn
DIE_SECONDS = 1.2          # how long a die tumbles
AFTER_DIE_SECONDS = 0.3    # the AI looks at its die before it moves
HOP_HEIGHT = 0.55          # how high a hop goes, in squares
LONG_HOP_HEIGHT = 1.0      # a long jump (out of the yard) goes higher
FLY_HEIGHT = 1.8           # how high a captured token flies
CONFETTI_SECONDS = 3.0     # how long the winner's confetti falls
PULSE_MS = 45              # how often the glowing rings change
LOG_LIMIT = 60             # the game log shows the latest 60 lines

MAX_PHOTOS = 700           # more pictures than this: forget the one-off ones

# How the dice look before anybody has rolled in a new game: a cube seen from
# a corner, so that three faces show (it does not claim any number). After a
# roll the die turns to show the number that was rolled big and clear in
# front (see ui_dice.REST_TILT).
IDLE_FACES = {HUMAN: 5, AI: 3}    # the face that looks at the player
IDLE_TILT = (27.0, -33.0)         # how far the idle cube is turned

# The rules page (one string per bullet point).
RULES = (
    "You are red (top-right), the AI is blue (bottom-left). Both go "
    "clockwise round the board.",
    "Roll the die, then choose a token. No 6 is needed to leave the yard.",
    "After one lap a token turns into its coloured home column and walks "
    "to the centre.",
    "Land on an opponent token and it goes back to its yard. START squares "
    "and star squares are safe.",
    "No exact roll is needed, and a 6 gives no extra turn.",
    "The first player to bring both tokens to the centre wins.",
    "Keys: Space = roll / play again, 1 or 2 = choose a token, "
    "N = new game, M = sound on / off.",
)


# ===== 2. HELPERS (they only calculate; none touches the window) =====

# Smooth start and stop for a movement (slow, fast, slow). Returns the eased
# progress, also from 0.0 to 1.0.
# Parameters:
#   u - animation progress from 0.0 (start) to 1.0 (end)
def ease_in_out(u):
    return u * u * (3 - 2 * u)


# Fast start and a slow finish (a die slowing down). Returns the eased
# progress, also from 0.0 to 1.0.
# Parameters:
#   u - animation progress from 0.0 (start) to 1.0 (end)
def ease_out(u):
    return 1 - (1 - u) * (1 - u)


# Picks a random direction in space (the axis a die spins round). Returns a
# list of three numbers [x, y, z] with length 1.
def random_axis():
    while True:
        axis = [random.gauss(0.0, 1.0) for _ in range(3)]
        length = math.sqrt(sum(part * part for part in axis))
        if length > 0.2:
            return [part / length for part in axis]


# Describes a token's progress in words for messages and buttons. Returns
# "yard", "step 12", "home 3" (home column) or "centre".
# Parameters:
#   progress - steps the token has moved (0 to 57)
def position_text(progress):
    if progress == START:
        return "yard"
    if progress == FINISH:
        return "centre"
    if progress >= HOME_COLUMN_FIRST:
        return f"home {progress - HOME_COLUMN_FIRST + 1}"
    return f"step {progress}"


# Tells whether a token that reaches this progress stands on a safe ring square
# (a START square or a star square). Returns True or False.
# Parameters:
#   player   - the player number (HUMAN = red, AI = blue)
#   progress - steps a token has moved (0 = yard, 57 = FINISH)
def lands_on_safe_square(player, progress):
    return ring_square(player, progress) in SAFE_RING_SQUARES


# Says what a move does besides moving: it captures, reaches the centre or
# lands on a safe square. Returns "capture", "centre", "safe" or None (an
# ordinary move).
# Parameters:
#   state       - the current GameState (token positions and whose turn it is)
#   token_index - which token of the player moves (0 or 1)
#   dice        - the number rolled on the die (1 to 6)
def move_tag(state, token_index, dice):
    player = state.current_player
    landing = destination(state.tokens[player][token_index], dice)
    if is_capture(state, token_index, dice):
        return "capture"
    if landing == FINISH:
        return "centre"
    if lands_on_safe_square(player, landing):
        return "safe"
    return None


# Builds a readable sentence for a move for the game log, e.g. "moved Token 2
# (step 4 → step 9) and landed on a safe square". Returns a string.
# Parameters:
#   state       - the current GameState (token positions and whose turn it is)
#   token_index - which token of the player moves (0 or 1)
#   dice        - the number rolled on the die (1 to 6)
def describe_move(state, token_index, dice):
    player = state.current_player
    start = state.tokens[player][token_index]
    landing = destination(start, dice)
    text = (f"moved Token {token_index + 1} "
            f"({position_text(start)} → {position_text(landing)})")
    tag = move_tag(state, token_index, dice)
    if tag == "capture":
        text += " and CAPTURED an opponent token!"
    elif tag == "centre":
        text += " and reached the centre"
    elif tag == "safe":
        text += " and landed on a safe square"
    return text


# Works out which grid cell a token with this progress stands on. Returns (row,
# column) for a ring or home-column square, the text "centre" for FINISH, and
# None while the token is in its yard.
# Parameters:
#   player   - the player number (HUMAN = red, AI = blue)
#   progress - steps a token has moved (0 = yard, 57 = FINISH)
def cell_of_progress(player, progress):
    if progress == START:
        return None
    if progress == FINISH:
        return "centre"
    if progress >= HOME_COLUMN_FIRST:
        return ui_art.HOME_COLUMN_CELLS[player][progress - HOME_COLUMN_FIRST]
    return ui_art.RING_CELLS[ring_square(player, progress)]


# Works out where a token waits inside its yard (in rows of two, on the plate).
# Returns a Slot.
# Parameters:
#   player - the player number (HUMAN = red, AI = blue)
#   index  - which token (0 or 1)
def yard_slot(player, index):
    x, y = ui_art.yard_slot_cell(player, index, TOKENS_PER_PLAYER)
    return Slot(x, y, YARD_SCALE)


# Works out where a finished token rests in the centre: yours in the red
# triangle at the top, the AI's in the blue triangle at the bottom. Returns a
# Slot.
# Parameters:
#   player - the player number (HUMAN = red, AI = blue)
#   index  - which token (0 or 1)
def centre_slot(player, index):
    crowded = TOKENS_PER_PLAYER > 2          # smaller tokens if there are many
    spacing, scale = (0.5, 0.55) if crowded else (0.7, CENTRE_SCALE)
    centre_x = 7.5 + (index - (TOKENS_PER_PLAYER - 1) / 2) * spacing
    centre_y = 6.5 if player == HUMAN else 8.5
    return Slot(centre_x, centre_y, scale)


# Works out where a token stands when it is the only token on its square (this
# is also the square it passes while it hops). Returns a Slot.
# Parameters:
#   player   - the player number (HUMAN = red, AI = blue)
#   index    - which token (0 or 1)
#   progress - steps a token has moved (0 = yard, 57 = FINISH)
def square_slot(player, index, progress):
    cell = cell_of_progress(player, progress)
    if cell is None:
        return yard_slot(player, index)
    if cell == "centre":
        return centre_slot(player, index)
    row, column = cell
    return Slot(column + 0.5, row + 0.5, 1.0)


# Works out where every token stands when nothing moves. Tokens that share a
# square (for example on a safe square) are placed side by side. Returns
# {(player, token index): Slot}
# Parameters:
#   state - the current GameState (token positions and whose turn it is)
def resting_layout(state):
    slots = {}
    sharing = {}                     # {(row, column): [(player, index), ...]}
    for player in (HUMAN, AI):
        for index, progress in enumerate(state.tokens[player]):
            cell = cell_of_progress(player, progress)
            if cell is None or cell == "centre":
                slots[(player, index)] = square_slot(player, index, progress)
            else:
                sharing.setdefault(cell, []).append((player, index))
    for (row, column), members in sharing.items():
        layout = STACK_LAYOUTS[min(len(members), 4)]
        for number, key in enumerate(members):
            shift_x, shift_y, scale = layout[number % len(layout)]
            slots[key] = Slot(column + 0.5 + shift_x, row + 0.5 + shift_y,
                              scale)
    return slots


# On Windows, tells the system that this program draws itself sharply on a
# high-resolution screen (otherwise Windows stretches the window and the
# pictures look blurry). Does nothing on other systems.
def enable_sharp_text():
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


# ===== 3. THE GAME WINDOW =====
class LudoApp:

    # Opens the window, then (a moment later, so the window is already visible)
    # shows the start page. The board is painted after START GAME is clicked.
    # Parameters:
    #   root - the Tkinter main window
    def __init__(self, root):
        self.root = root
        # 1.0 on a normal screen, 1.5 on a "150 %" screen, and so on.
        self.ui = max(1.0, root.winfo_fpixels("1i") / 96.0)
        root.title(f"Ludo Duel  |  {STUDENT_NAME} ({STUDENT_ID})")
        root.configure(bg=BACKGROUND)
        try:
            self.icon = ImageTk.PhotoImage(ui_art.render_app_icon(64),
                                           master=root)
            root.iconphoto(True, self.icon)
        except tk.TclError:
            pass                           # the default icon is fine too

        # Settings the player can change.
        self.difficulty = "Medium"
        self.first_player = "You"
        self.speed_name = "Normal"
        self.speed = SPEEDS[self.speed_name]

        # The game.
        self.state = new_game(HUMAN)
        self.phase = "busy"              # "roll", "choose", "busy" or "over"
        self.dice = None                 # your roll, until you move
        self.scores = {HUMAN: 0, AI: 0}  # games won since the program started
        self.landing = {}                # {player: progress last landed on}

        # The dice: the number each one shows (None = not rolled yet in this
        # game), how it is turned, whether it is tumbling right now, and the
        # pictures of the resting faces.
        self.die_value = {HUMAN: None, AI: None}
        self.die_twist = {HUMAN: -6.0, AI: 5.0}
        self.rolling = {HUMAN: False, AI: False}
        self.die_cache = {}

        # The texts of the panel.
        self.status = ("", "", HUMAN_INK)    # title, help line, colour
        self.status_die = None               # (player, number) or None
        self.log_entries = []                # [(kind, text), ...]
        self.thinking = (None, 0, [])        # dice, depth, rows
        self.tab = 0                         # 0 log, 1 AI thinking, 2 rules
        self.scroll = [0, 0, 0]              # scroll position of each page
        self.pages = {}                      # painted pages, by tab

        # The picture. display[(player, index)] = [x, y, lift, scale]: where
        # a token is drawn right now (x and y in squares, lift = how far it
        # is off the ground in squares).
        self.scene = None
        self.size = (0, 0)
        self.ready = False
        self.items = {}                  # canvas items by name
        self.shown = {}                  # the picture each item shows now
        self.live = {}                   # photos that are replaced every frame
        self.photos = {}                 # photos of the scene's pictures
        self.hotspots = []               # clickable areas: (name, region)
        self.display = {}
        self.halo_keys = set()           # tokens that can be chosen now
        self.halo_step = 0
        self.frame_step = 3
        self.pulse_phase = 0.0
        self.hover = None                # the clickable thing under the mouse
        self.pressed = None              # the thing the mouse button is on
        self.resize_job = None

        # The animation that is playing (a generator, see run()).
        self.script = None
        self.script_job = None

        # The start page (shown until START GAME is clicked).
        self.on_start_page = True
        self.start_button = None         # (pictures by state, x, y)
        self.start_region = (0, 0, 0, 0)
        self.start_state = "normal"      # "normal", "hover" or "press"
        self.player_name = "You"         # Player 1's name, typed on the start page
        self.name_entry = None

        # The sound effects (M turns them on and off).
        self.sound = SoundPlayer()

        self.build_window()
        self.bind_keys()
        root.after(30, self.show_start_page)

    # ===== THE WINDOW AND ITS PICTURES =====

    # Creates the one canvas that fills the window and sizes the window so that
    # the whole design fits on this screen.
    def build_window(self):
        root = self.root
        self.canvas = tk.Canvas(root, bg=BACKGROUND, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Leave>", self.on_leave)
        for event in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind(event, self.on_wheel)

        screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
        k = min(self.ui, (screen_w - 60) / ui_art.DESIGN_W,
                (screen_h - 120) / ui_art.DESIGN_H)
        k = max(k, 0.62)
        width, height = int(ui_art.DESIGN_W * k), int(ui_art.DESIGN_H * k)
        left = max(0, (screen_w - width) // 2)
        top = max(0, (screen_h - height) // 2 - 20)
        root.geometry(f"{width}x{height}+{left}+{top}")
        root.minsize(int(ui_art.DESIGN_W * 0.62), int(ui_art.DESIGN_H * 0.62))
        self.canvas.create_text(width / 2, height / 2, text="Loading Ludo Duel...",
                                fill="#9fb4de", font=("Helvetica", 16),
                                tags="loading")
        root.update()

    # Connects the keyboard: Space / Enter roll the die, 1 and 2 choose a
    # token, N starts a new game.
    def bind_keys(self):
        self.root.bind("<space>", lambda event: None if self.typing()
                       else self.on_primary())
        self.root.bind("<Return>", lambda event: self.on_primary())
        for index in range(TOKENS_PER_PLAYER):
            self.root.bind(str(index + 1), lambda event, i=index: None
                           if self.typing() else self.on_choose(i))
        for key in ("n", "N"):
            self.root.bind(key, lambda event: None if self.on_start_page
                           else self.start_new_game())
        for key in ("m", "M"):
            self.root.bind(key, lambda event: None if self.typing()
                           else self.toggle_sound())

    # Is the person typing their name in the box on the start page?
    def typing(self):
        return (self.name_entry is not None
                and self.root.focus_get() is self.name_entry)

    # "Your" or "Selvaraj's", for the status messages.
    def your_word(self):
        return "Your" if self.player_name == "You" else f"{self.player_name}'s"

    # Turns the sound effects on or off (key M) and says so in the game log.
    def toggle_sound(self):
        on = self.sound.toggle()
        if not self.on_start_page and self.ready:
            self.add_log(None, "Sound on" if on else "Sound off (press M)")

    # ===== THE START PAGE =====

    # Paints the start page for the current window size: the logo, the two
    # player profiles, the student card and the START GAME button.
    def show_start_page(self):
        self.resize_job = None
        if not self.on_start_page:
            return
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 300 or height < 200:
            self.root.after(50, self.show_start_page)
            return
        self.size = (width, height)
        page = ui_start.render_start_page(width, height, STUDENT, name_box=True)
        pictures = {}
        for state in ("normal", "hover", "press"):
            picture, x, y = ui_start.render_start_button(width, height, state)
            pictures[state] = ImageTk.PhotoImage(picture, master=self.root)
        self.start_photo = ImageTk.PhotoImage(page, master=self.root)
        self.start_button = (pictures, x, y)
        self.start_region = ui_start.start_button_region(width, height)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.start_photo,
                                 tags="start")
        self.canvas.create_image(x, y, anchor="nw", tags=("start", "start_btn"),
                                 image=pictures[self.start_state])
        self.place_name_box(width, height)

    # Puts the text box for Player 1's name on the start page.
    # Parameters:
    #   width  - width in pixels
    #   height - height in pixels
    def place_name_box(self, width, height):
        bx, by, bw, bh = ui_start.name_box_region(width, height)
        size = -max(12, int(bh * 0.56))
        if self.name_entry is None:
            self.name_entry = tk.Entry(
                self.root, bg="#060f2c", fg="#ffffff", insertbackground="#ffffff",
                relief="flat", highlightthickness=2, highlightcolor="#ffbe04",
                highlightbackground="#3a63c4", justify="left")
            self.name_entry.insert(0, NAME_HINT)
            self.name_entry.configure(fg="#7d8fb8")
            self.name_entry.bind("<FocusIn>", self.on_name_focus)
        self.name_entry.configure(font=("Segoe UI", size, "bold"))
        self.canvas.create_window(bx, by, anchor="nw", width=bw, height=bh,
                                  window=self.name_entry, tags="start")

    # Clears the grey hint when the person clicks into the name box.
    # Parameters:
    #   event - the Tkinter event (holds the mouse position)
    def on_name_focus(self, event):
        if self.name_entry.get() == NAME_HINT:
            self.name_entry.delete(0, "end")
            self.name_entry.configure(fg="#ffffff")

    # The name typed on the start page ("You" if the box is empty).
    def read_name(self):
        if self.name_entry is None:
            return "You"
        text = " ".join(self.name_entry.get().split())[:14]
        return text if text and text != NAME_HINT else "You"

    # Shows the START GAME button as normal, highlighted or pressed.
    # Parameters:
    #   state - the current GameState (token positions and whose turn it is)
    def set_start_state(self, state):
        if state == self.start_state or self.start_button is None:
            return
        self.start_state = state
        self.canvas.itemconfigure("start_btn", image=self.start_button[0][state])
        self.canvas.configure(cursor="" if state == "normal" else "hand2")

    # Is the point (x, y) on the START GAME button?
    # Parameters:
    #   x - mouse x in pixels
    #   y - mouse y in pixels
    def over_start_button(self, x, y):
        x1, y1, x2, y2 = self.start_region
        return x1 <= x <= x2 and y1 <= y <= y2

    # START GAME was clicked (or Enter / Space pressed): the start page closes
    # and the board is painted, then the first game begins.
    def leave_start_page(self):
        if not self.on_start_page:
            return
        self.sound.play("start")
        self.player_name = self.read_name()
        if self.name_entry is not None:
            self.name_entry.destroy()
            self.name_entry = None
        self.root.focus_set()
        self.on_start_page = False
        self.start_button = self.start_photo = None
        self.canvas.delete("all")
        self.canvas.configure(cursor="")
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_text(width / 2, height / 2, text="Loading Ludo Duel...",
                                fill="#9fb4de", font=("Helvetica", 16),
                                tags="loading")
        self.size = (0, 0)
        self.root.after(30, self.first_build)

    # Paints the pictures for the first time and starts the first game.
    def first_build(self):
        self.rebuild_scene()
        self.ready = True
        self.canvas.delete("loading")
        self.start_new_game()
        self.pulse()

    # The window changed size: paint the pictures again shortly after the
    # resizing stops (so dragging the window edge stays smooth).
    # Parameters:
    #   event - the Tkinter event (holds the mouse position)
    def on_resize(self, event):
        if (event.width, event.height) == self.size:
            return
        if self.on_start_page:                 # repaint the start page
            if self.resize_job is not None:
                self.root.after_cancel(self.resize_job)
            self.resize_job = self.root.after(150, self.show_start_page)
            return
        if not self.ready:
            return
        if self.resize_job is not None:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(150, self.rebuild_scene)

    # Paints every picture for the current window size (about one second) and
    # puts everything where it belongs. The game itself is not touched, so this
    # also works in the middle of a game.
    def rebuild_scene(self):
        self.resize_job = None
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 300 or height < 200:
            return
        self.scene = ui_art.Scene(width, height, TOKENS_PER_PLAYER,
                                  SAFE_RING_SQUARES, STUDENT, self.player_name)
        self.size = (width, height)
        self.photos, self.die_cache, self.pages = {}, {}, {}
        for scale in WARM_SCALES:                    # paint the pawns now
            for player in (HUMAN, AI):
                for index in range(TOKENS_PER_PLAYER):
                    self.scene.pawn_picture(player, index, scale)
        for step in range(ui_art.BOOM_STEPS + 1):
            self.scene.boom_picture(step / ui_art.BOOM_STEPS)
        self.build_items()
        self.refresh_all()

    # Creates the canvas items: the big still picture first, then every picture
    # that moves or changes (buttons, texts, dice, tokens ...) from bottom to
    # top. Each item starts hidden; show() fills it.
    def build_items(self):
        canvas, scene = self.canvas, self.scene
        canvas.delete("all")
        self.items, self.shown, self.live = {}, {}, {}
        self.still = ImageTk.PhotoImage(scene.still, master=self.root)
        canvas.create_image(0, 0, anchor="nw", image=self.still)

        keys = [(player, index) for player in (HUMAN, AI)
                for index in range(TOKENS_PER_PLAYER)]
        corner = ["seg_difficulty", "seg_first", "seg_speed", "btn_new",
                  "btn_roll", "btn_tok0", "btn_tok1", "status_die",
                  "status_title", "status_sub", "page"]
        corner += [("tab", index) for index in range(3)]
        for player in (HUMAN, AI):
            corner += [("score", player), ("circles", player),
                       ("homes", player), ("marker", player),
                       ("frame", player), ("floor", player)]
        corner.append("preview")
        centred = [("die", player) for player in (HUMAN, AI)]
        centred += [("shadow", key) for key in keys]
        centred += [("halo", key) for key in keys]
        centred += [("pawn", key) for key in keys] + ["boom"]
        for name in corner:
            self.items[name] = canvas.create_image(0, 0, anchor="nw",
                                                   state="hidden")
        for name in centred:
            self.items[name] = canvas.create_image(0, 0, anchor="center",
                                                   state="hidden")
        # The thin bar at the right edge of the panel that shows how far the
        # page is scrolled (only visible when the page is longer).
        self.scrollbar = canvas.create_line(
            0, 0, 0, 0, fill="#4f7ccc", capstyle="round", state="hidden",
            width=max(3, int(round(4 * scene.k))))

        self.hotspots = [
            ("new", scene.button_region(ui_art.NEW_GAME_BOX)),
            ("roll", scene.button_region(ui_art.ROLL_BOX)),
            ("tok0", scene.button_region(ui_art.TOKEN_BOXES[0])),
            ("tok1", scene.button_region(ui_art.TOKEN_BOXES[1])),
            ("tab0", scene.tab_region(0)), ("tab1", scene.tab_region(1)),
            ("tab2", scene.tab_region(2)),
            ("difficulty", scene.segment_region("difficulty")),
            ("first", scene.segment_region("first")),
            ("speed", scene.segment_region("speed")),
            ("die", scene.die_region(HUMAN)),
        ]

    # Gives the Tk photo for one of the scene's pictures. Photos are made the
    # first time and then kept (the scene keeps its pictures too). Returns an
    # ImageTk.PhotoImage.
    # Parameters:
    #   picture - PIL image to turn into a Tkinter image
    def photo_of(self, picture):
        entry = self.photos.get(id(picture))
        if entry is None or entry[0] is not picture:
            entry = (picture, ImageTk.PhotoImage(picture, master=self.root))
            self.photos[id(picture)] = entry
        return entry[1]

    # Puts one of the scene's pictures on a canvas item and moves the item.
    # Parameters:
    #   name    - name of the canvas item
    #   picture - a PIL RGBA image
    #   x       - horizontal position in pixels
    #   y       - vertical position in pixels
    def show(self, name, picture, x, y):
        item = self.items[name]
        if self.shown.get(name) is not picture:
            self.canvas.itemconfigure(item, image=self.photo_of(picture),
                                      state="normal")
            self.shown[name] = picture
        self.canvas.coords(item, x, y)

    # Like show(), for a picture that is used only once (a frame of the
    # tumbling die, a page of the log). Its photo is dropped as soon as the
    # next picture replaces it.
    # Parameters:
    #   name    - name of the canvas item
    #   picture - a PIL RGBA image
    #   x       - horizontal position in pixels
    #   y       - vertical position in pixels
    def show_fresh(self, name, picture, x, y):
        item = self.items[name]
        photo = ImageTk.PhotoImage(picture, master=self.root)
        self.canvas.itemconfigure(item, image=photo, state="normal")
        self.canvas.coords(item, x, y)
        self.live[name] = photo
        self.shown.pop(name, None)

    # Hides a canvas item.
    # Parameters:
    #   name - name of the canvas item
    def hide(self, name):
        if self.shown.get(name, 0) is None:
            return
        self.canvas.itemconfigure(self.items[name], state="hidden")
        self.shown[name] = None
        self.live.pop(name, None)

    # Puts every picture of the window in its right state: controls, texts,
    # scoreboard, board and dice.
    def refresh_all(self):
        if self.scene is None:
            return
        self.refresh_controls()
        self.refresh_page()
        self.refresh_status()
        self.refresh_scores()
        self.place_everything()

    # ===== DRAWING THE BOARD (tokens, landing frames, dice) =====

    # Works out where a token's middle is on the screen right now. Returns (x,
    # y) in pixels.
    # Parameters:
    #   key - which pawn: a (player, token index) pair
    def pawn_centre(self, key):
        x, y, lift, _ = self.display[key]
        px, ground = self.scene.grid_pos(x, y)
        return px, ground - lift * self.scene.cell

    # Moves the pictures of one token (its shadow, its glowing ring and the
    # pawn itself) to where self.display says it is now.
    # Parameters:
    #   key - which pawn: a (player, token index) pair
    def place_pawn(self, key):
        scene = self.scene
        if scene is None or key not in self.display:
            return
        player, index = key
        x, y, lift, scale = self.display[key]
        px, ground = scene.grid_pos(x, y)
        top = ground - lift * scene.cell
        radius = scene.pawn_radius(scale)
        self.show(("shadow", key), scene.shadow_picture(scale, lift), px,
                  ground + radius * 0.55)
        self.show(("pawn", key), scene.pawn_picture(player, index, scale),
                  px, top)
        if key in self.halo_keys:
            self.show(("halo", key), scene.halo_picture(scale, self.halo_step),
                      px, top)
        else:
            self.hide(("halo", key))

    # Lifts a token's picture above the other tokens (the one that moves must
    # never go behind another token).
    # Parameters:
    #   key - which pawn: a (player, token index) pair
    def raise_pawn(self, key):
        self.canvas.tag_raise(self.items[("pawn", key)])
        self.canvas.tag_raise(self.items["boom"])

    # Puts a player's landing frame round the square the player's token last
    # landed on (or hides it).
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    def place_marker(self, player):
        progress = self.landing.get(player)
        cell = None if progress is None else cell_of_progress(player, progress)
        if self.scene is None:
            return
        if cell is None or cell == "centre":
            self.hide(("marker", player))
            return
        row, column = cell
        x, y = self.scene.marker_origin(row, column)
        self.show(("marker", player), self.scene.marker_picture(player), x, y)

    # How strongly a die's frame glows: brightest while the die tumbles,
    # pulsing while it is your turn to roll. Returns a number from 0 to 5.
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    def frame_level(self, player):
        if self.rolling[player]:
            return 5
        if player == HUMAN and self.phase == "roll":
            return self.frame_step
        return 3 if player == HUMAN else 2

    # Draws a die's glowing frame at its current glow strength.
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    def place_frame(self, player):
        scene = self.scene
        if scene is None:
            return
        x, y = scene.die_frame_origin(player)
        self.show(("frame", player),
                  scene.die_frame_picture(player, self.frame_level(player)),
                  x, y)

    # The picture of a die lying still. After a roll it shows the number that
    # was rolled as the big face in front; before the first roll of a game it
    # is a cube seen from a corner (no number is claimed). Each picture is
    # painted the first time it is needed and then kept. Returns a PIL image.
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    def resting_die(self, player):
        value = self.die_value[player]
        picture = self.die_cache.get((player, value))
        if picture is None:
            if value is None:
                rotation = resting_rotation(IDLE_FACES[player],
                                            twist=self.die_twist[player],
                                            tilt=IDLE_TILT)
            else:
                rotation = resting_rotation(value, twist=self.die_twist[player])
            picture = self.scene.die_picture(player, rotation)
            self.die_cache[(player, value)] = picture
        return picture

    # Draws one die in its frame: the soft shadow under it and the die itself
    # (lying still, or in the given position while it tumbles).
    # Parameters:
    #   player  - the player number (HUMAN = red, AI = blue)
    #   picture - picture of the die, or None for the die at rest
    #   lift    - how high the pawn is lifted (0 = on the board)
    def place_die(self, player, picture=None, lift=0.0):
        scene = self.scene
        if scene is None:
            return
        cx, cy = scene.grid_pos(*ui_art.DIE_CENTRE[player])
        shadow, (dx, dy) = scene.floor_shadow_picture()
        self.show(("floor", player), shadow, cx + dx, cy + dy)
        if picture is None:
            self.show(("die", player), self.resting_die(player), cx, cy)
        else:
            self.show_fresh(("die", player), picture, cx,
                            cy - lift * scene.cell)

    # Puts every token, both landing frames and both dice where they belong
    # right now.
    def place_everything(self):
        for key in self.display:
            self.place_pawn(key)
        for player in (HUMAN, AI):
            self.place_marker(player)
            self.place_frame(player)
            self.place_die(player)

    # ===== DRAWING THE PANEL (status, scores, buttons, tabs, pages) =====

    # Changes the big message in the status card.
    # Parameters:
    #   title  - the big headline
    #   sub    - the small help line
    #   colour - colour of the headline
    #   die    - number for the small die, or None
    def set_status(self, title, sub="", colour=HUMAN_INK, die=None):
        self.status = (title, sub, colour)
        self.status_die = die
        self.refresh_status()

    # Draws the little die, the headline and the help line of the status card.
    def refresh_status(self):
        scene = self.scene
        if scene is None:
            return
        player, number = self.status_die or (HUMAN, None)
        picture = scene.status_die_picture(player, number)
        x, y = scene.status_die_origin(picture)
        self.show("status_die", picture, x, y)
        title, sub, colour = self.status
        picture, (x, y) = scene.text_slot(STATUS_TITLE_BOX, title, "bold", 29,
                                          colour)
        self.show("status_title", picture, x, y)
        if sub:
            picture, (x, y) = scene.text_slot(STATUS_SUB_BOX, sub, "regular",
                                              14.5, ui_art.TEXT)
            self.show("status_sub", picture, x, y)
        else:
            self.hide("status_sub")

    # Draws the scoreboard: for each side the games won and a row of circles
    # that fill up as tokens reach the centre.
    def refresh_scores(self):
        scene = self.scene
        if scene is None:
            return
        for player in (HUMAN, AI):
            home = sum(1 for progress in self.state.tokens[player]
                       if progress == FINISH)
            picture, (x, y) = scene.text_slot(
                SCORE_BOX[player], str(self.scores[player]), "bold", 31,
                ui_art.WHITE, "r")
            self.show(("score", player), picture, x, y)
            picture, (x, y) = scene.home_circles(player, home)
            self.show(("circles", player), picture, x, y)
            picture, (x, y) = scene.text_slot(
                HOME_TEXT_BOX[player], f"{home}/{TOKENS_PER_PLAYER} home",
                "regular", 14.2, ui_art.MUTED)
            self.show(("homes", player), picture, x, y)

    # Tells whether a clickable thing is on the screen right now (the ROLL
    # button is replaced by the token buttons while you choose a token).
    # Returns True or False.
    # Parameters:
    #   name - name of the button
    def is_visible(self, name):
        if name == "roll":
            return self.phase != "choose"
        if name.startswith("tok"):
            return (self.phase == "choose"
                    and int(name[3:]) in get_legal_moves(self.state))
        return True

    # Tells whether a clickable thing reacts to a click right now. Returns True
    # or False.
    # Parameters:
    #   name - name of the button
    def is_enabled(self, name):
        if name == "roll":
            return self.phase in ("roll", "over")
        if name == "die":
            return self.phase == "roll"
        if name.startswith("tok") or name.startswith("pawn"):
            return (self.phase == "choose"
                    and int(name[-1]) in get_legal_moves(self.state))
        return True

    # How a button looks right now. Returns "off", "press", "hover" or
    # "normal".
    # Parameters:
    #   name - name of the button
    def button_state(self, name):
        if not self.is_enabled(name):
            return "off" if name == "roll" else "normal"
        if self.hover == name:
            return "press" if self.pressed == name else "hover"
        return "normal"

    # The two lines on the button that moves one of your tokens. Returns (first
    # line, second line), e.g. ("Token 1", "step 4 → step 9 · capture").
    # Parameters:
    #   index - which token button (0 or 1)
    def token_button_text(self, index):
        start = self.state.tokens[HUMAN][index]
        line = (f"{position_text(start)} → "
                f"{position_text(destination(start, self.dice))}")
        tag = move_tag(self.state, index, self.dice)
        if tag:
            line += f" · {tag}"
        return f"Token {index + 1}", line

    # Draws the buttons and tabs for the current phase: ROLL DICE (or PLAY
    # AGAIN when the game is over), the token buttons after you rolled, the
    # settings, NEW GAME and the tabs. (The page under the tabs is drawn by
    # refresh_page.)
    def refresh_controls(self):
        scene = self.scene
        if scene is None:
            return
        for name, chosen in (("difficulty", self.difficulty),
                             ("first", self.first_player),
                             ("speed", self.speed_name)):
            x, y = scene.segment_region(name)[:2]
            self.show("seg_" + name, scene.segment_picture(name, chosen), x, y)
        self.show("btn_new", scene.button_picture("new", "NEW GAME",
                                                  self.button_state("new")),
                  *scene.button_origin(ui_art.NEW_GAME_BOX))

        if self.phase == "choose":
            self.hide("btn_roll")
            legal = get_legal_moves(self.state)
            for index in range(TOKENS_PER_PLAYER):
                if index in legal:
                    one, two = self.token_button_text(index)
                    picture = scene.token_button_picture(
                        index, one, two, self.button_state(f"tok{index}"))
                    self.show(f"btn_tok{index}", picture,
                              *scene.token_button_origin(index))
                else:
                    self.hide(f"btn_tok{index}")
        else:
            for index in range(TOKENS_PER_PLAYER):
                self.hide(f"btn_tok{index}")
            label = "PLAY AGAIN" if self.phase == "over" else "ROLL DICE"
            self.show("btn_roll", scene.button_picture(
                "roll", label, self.button_state("roll")),
                *scene.button_origin(ui_art.ROLL_BOX))

        for index in range(3):
            hover = self.hover == f"tab{index}" and index != self.tab
            x, y = scene.tab_region(index)[:2]
            self.show(("tab", index),
                      scene.tab_picture(index, index == self.tab, hover), x, y)
        self.refresh_preview()

    # While the mouse is over a token's button (or the glowing token), a gold
    # frame shows the square that token would land on - handy to see a capture
    # or a safe square before you decide.
    def refresh_preview(self):
        scene = self.scene
        if scene is None:
            return
        if (self.phase == "choose" and self.hover is not None
                and self.hover[:3] in ("tok", "paw")):
            index = int(self.hover[-1])
            if index in get_legal_moves(self.state):
                landing = destination(self.state.tokens[HUMAN][index],
                                      self.dice)
                cell = cell_of_progress(HUMAN, landing)
                if cell is not None and cell != "centre":
                    x, y = scene.marker_origin(*cell)
                    self.show("preview", scene.marker_picture("preview"), x, y)
                    return
        self.hide("preview")

    # The painted page (game log, AI thinking or rules) of a tab, as tall as
    # its content. Pages are painted when first needed and again after their
    # content changed. Returns a PIL image.
    # Parameters:
    #   tab - tab number (0 log, 1 AI thinking, 2 rules)
    def page_image(self, tab):
        page = self.pages.get(tab)
        if page is None:
            scene = self.scene
            x1, _, x2, _ = scene.page_region()
            width = x2 - x1
            if tab == 0:
                page = ui_art.render_log_page(self.log_entries[-LOG_LIMIT:],
                                              width, scene.k)
            elif tab == 1:
                dice, depth, rows = self.thinking
                page = ui_art.render_thinking_page(dice, depth, rows, width,
                                                   scene.k)
            else:
                page = ui_art.render_rules_page(RULES, width, scene.k)
            self.pages[tab] = page
        return page

    # Shows the visible part of the chosen page inside the panel (the page can
    # be longer than the panel; the mouse wheel scrolls it).
    def refresh_page(self):
        scene = self.scene
        if scene is None:
            return
        x1, y1, x2, y2 = scene.page_region()
        page = self.page_image(self.tab)
        limit = max(0, page.height - (y2 - y1))
        offset = max(0, min(limit, self.scroll[self.tab]))
        self.scroll[self.tab] = offset
        view = page.crop((0, offset, x2 - x1, offset + (y2 - y1)))
        self.show_fresh("page", view, x1, y1)
        if limit > 0:
            height, k = y2 - y1, scene.k
            thumb = max(24 * k, height * height / float(page.height))
            top = y1 + 4 * k + offset / float(limit) * (height - 8 * k - thumb)
            x = x2 - 6 * k
            self.canvas.coords(self.scrollbar, x, top, x, top + thumb)
            self.canvas.itemconfigure(self.scrollbar, state="normal")
        else:
            self.canvas.itemconfigure(self.scrollbar, state="hidden")

    # Adds one line to the game log (the log scrolls down to it).
    # Parameters:
    #   player - who did it (HUMAN, AI or None for info)
    #   text   - the line to add
    def add_log(self, player, text):
        kind = {HUMAN: "you", AI: "ai"}.get(player, "info")
        self.log_entries.append((kind, text))
        self.pages.pop(0, None)
        self.scroll[0] = 10 ** 9                  # (limited to the end)
        if self.tab == 0:
            self.refresh_page()

    # Empties the game log (a new game starts).
    def clear_log(self):
        self.log_entries = []
        self.pages.pop(0, None)
        self.scroll[0] = 0

    # Fills the "AI Thinking" tab with what the AI worked out: the value of
    # each token it could move, and which one it played.
    # Parameters:
    #   dice  - the number rolled on the die (1 to 6)
    #   depth - how many moves ahead the search looks
    #   rows  - list of (token, move, value, chosen) rows of the AI search
    def show_thinking(self, dice, depth, rows):
        self.thinking = (dice, depth, rows)
        self.pages.pop(1, None)
        self.scroll[1] = 0
        if self.tab == 1:
            self.refresh_page()

    # ===== INPUT (clicks, keys, buttons) =====

    # Finds the clickable thing under the mouse pointer: a button, a tab, a
    # setting, your die, or a glowing token. Returns the name of the thing
    # ("new", "roll", "tok0", "tab1", "die", "pawn0", ...) or None.
    # Parameters:
    #   x - mouse x in pixels
    #   y - mouse y in pixels
    def hotspot_at(self, x, y):
        if self.scene is None:
            return None
        for name, (x1, y1, x2, y2) in self.hotspots:
            if x1 <= x <= x2 and y1 <= y <= y2 and self.is_visible(name):
                return name
        if self.phase == "choose":
            for key in self.halo_keys:
                px, py = self.pawn_centre(key)
                reach = self.scene.pawn_radius(self.display[key][3]) * 1.3
                if (x - px) ** 2 + (y - py) ** 2 <= reach * reach:
                    return f"pawn{key[1]}"
        return None

    # The mouse moved: highlights the button under it and shows a hand pointer
    # over everything that can be clicked.
    # Parameters:
    #   event - the Tkinter event (holds the mouse position)
    def on_motion(self, event):
        if self.on_start_page:
            if self.start_state != "press":
                self.set_start_state("hover" if self.over_start_button(
                    event.x, event.y) else "normal")
            return
        name = self.hotspot_at(event.x, event.y)
        if name != self.hover:
            self.hover = name
            self.refresh_controls()
        clickable = name is not None and self.is_enabled(name)
        self.canvas.configure(cursor="hand2" if clickable else "")

    # The mouse button went down: a button under the pointer looks pressed.
    # Parameters:
    #   event - the Tkinter event (holds the mouse position)
    def on_press(self, event):
        if self.on_start_page:
            if self.over_start_button(event.x, event.y):
                self.set_start_state("press")
            return
        name = self.hotspot_at(event.x, event.y)
        self.hover = name
        self.pressed = name if name and self.is_enabled(name) else None
        self.refresh_controls()

    # The mouse button went up: if it is still over the thing it went down on,
    # that thing is activated (a click).
    # Parameters:
    #   event - the Tkinter event (holds the mouse position)
    def on_release(self, event):
        if self.on_start_page:
            clicked = (self.start_state == "press"
                       and self.over_start_button(event.x, event.y))
            self.set_start_state("hover" if self.over_start_button(
                event.x, event.y) else "normal")
            if clicked:
                self.leave_start_page()
            return
        name = self.hotspot_at(event.x, event.y)
        pressed, self.pressed = self.pressed, None
        self.hover = name
        if pressed is not None and pressed == name:
            self.activate(name, event.x)
        self.refresh_controls()

    # The mouse left the window: nothing is highlighted any more.
    # Parameters:
    #   event - the Tkinter event (holds the mouse position)
    def on_leave(self, event):
        if self.on_start_page:
            self.set_start_state("normal")
            return
        self.hover = self.pressed = None
        self.refresh_controls()

    # The mouse wheel turned: scrolls the page of the panel if the pointer is
    # over it.
    # Parameters:
    #   event - the Tkinter event (holds the mouse position)
    def on_wheel(self, event):
        if self.scene is None:
            return
        x1, y1, x2, y2 = self.scene.page_region()
        if not (x1 <= event.x <= x2 and y1 <= event.y <= y2):
            return
        if event.num == 4:
            direction = -1
        elif event.num == 5:
            direction = 1
        else:
            direction = -1 if event.delta > 0 else 1
        self.scroll[self.tab] += direction * int(34 * self.scene.k)
        self.refresh_page()

    # Carries out a click on one of the clickable things.
    # Parameters:
    #   name - name of the clickable thing (e.g. "new", "roll", "tok0")
    #   x    - mouse x in pixels (picks the option in a row of choices)
    def activate(self, name, x):
        if name not in ("roll", "die") and not name.startswith(("tok", "pawn")):
            self.sound.play("click")          # the dice and hops have their own
        if name == "new":
            self.start_new_game()
        elif name in ("roll", "die"):
            self.on_primary()
        elif name.startswith("tok") or name.startswith("pawn"):
            self.on_choose(int(name[-1]))
        elif name.startswith("tab"):
            self.on_tab(int(name[3:]))
        else:
            self.on_setting(name, x)

    # Shows the page of the tab that was clicked (log, AI thinking, rules).
    # Parameters:
    #   index - tab number (0 log, 1 AI thinking, 2 rules)
    def on_tab(self, index):
        self.tab = index
        self.refresh_controls()
        self.refresh_page()

    # The player clicked one of the three rows of options. The option under the
    # pointer becomes the chosen one.
    # Parameters:
    #   name - which setting row ("level", "first", "speed")
    #   x    - mouse x in pixels (picks the option)
    def on_setting(self, name, x):
        options = ui_art.SEGMENTS[name]["options"]
        x1, _, x2, _ = self.scene.segment_region(name)
        index = min(len(options) - 1,
                    max(0, int((x - x1) / float(x2 - x1) * len(options))))
        option = options[index]
        if name == "difficulty":
            if option != self.difficulty:
                self.add_log(None, f"AI difficulty: {option}")
            self.difficulty = option          # used from the AI's next move
        elif name == "first":
            self.first_player = option        # used by the next new game
        else:
            self.speed_name = option
            self.speed = SPEEDS[option]
        self.refresh_controls()

    # The big button (or your die, or Space / Enter): closes the start page,
    # rolls the die when it is your turn to roll, and starts a new game when
    # the game is over.
    def on_primary(self):
        if self.on_start_page:
            self.leave_start_page()
        elif self.phase == "roll":
            self.on_roll()
        elif self.phase == "over":
            self.start_new_game()

    # The person rolls the die: locks the controls and plays the roll.
    def on_roll(self):
        if self.phase != "roll":
            return
        self.phase = "busy"
        self.refresh_controls()
        self.run(self.human_roll_script())

    # The person chose which token to move (button, click or key 1 / 2): locks
    # the controls and plays the move and then the AI's reply.
    # Parameters:
    #   token_index - which token of the player moves (0 or 1)
    def on_choose(self, token_index):
        if (self.phase != "choose"
                or token_index not in get_legal_moves(self.state)):
            return
        state, dice = self.state, self.dice
        self.phase = "busy"
        self.dice = None
        self.halo_keys = set()
        for key in self.display:
            self.place_pawn(key)                    # hides the glowing rings
        self.refresh_controls()
        self.add_log(HUMAN, f"{self.player_name} "
                            f"{describe_move(state, token_index, dice)}")
        self.run(self.human_move_script(state, token_index, dice))

    # ===== THE SCRIPT RUNNER AND ITS TOOLS =====

    # Starts an animation script (a generator). Whatever script was running is
    # stopped first.
    # Parameters:
    #   script - generator that runs an animation step by step
    def run(self, script):
        self.cancel_script()
        self.script = script
        self.step_script(script)

    # Runs a script up to its next `yield` and schedules the next step. The
    # time the step itself took is taken off the pause, so light frames run at
    # about 60 pictures a second and heavy frames as fast as they can.
    # Parameters:
    #   script - generator that runs an animation step by step
    def step_script(self, script):
        if script is not self.script:               # it was cancelled
            return
        started = time.perf_counter()
        try:
            delay = next(script)
        except StopIteration:
            self.script = None
            self.script_job = None
            return
        spent = (time.perf_counter() - started) * 1000.0
        if delay is None:
            milliseconds = max(1, int(FRAME_MS - spent))
        else:
            milliseconds = max(1, int(delay * 1000 - spent))
        self.script_job = self.root.after(milliseconds, self.step_script,
                                          script)

    # Stops the running animation (used when a new game starts).
    def cancel_script(self):
        if self.script_job is not None:
            self.root.after_cancel(self.script_job)
        if self.script is not None:
            self.script.close()
        self.script = None
        self.script_job = None

    # Script tool: pauses the script for a while (shorter on "Fast"). Use it
    # as: yield from self.wait(0.3)
    # Parameters:
    #   seconds - length of the animation in seconds
    def wait(self, seconds):
        yield seconds / self.speed

    # Script tool: plays a movement. `update` is called about 60 times a second
    # with the progress u going from 0 to 1, and one last time with exactly 1.0
    # so the movement always ends in the right place. Use it as: yield from
    # self.tween(0.2, update)
    # Parameters:
    #   seconds - length of the animation in seconds
    #   update  - function called with the progress 0.0..1.0 every frame
    def tween(self, seconds, update):
        seconds = seconds / self.speed
        started = time.perf_counter()
        while True:
            progress = (time.perf_counter() - started) / seconds
            if progress >= 1.0:
                break
            update(progress)
            yield None
        update(1.0)

    # Runs all the time: makes the rings round the tokens you can choose (and
    # the frame of your die when it is your turn to roll) grow and shrink so
    # they catch the eye.
    def pulse(self):
        self.pulse_phase += 0.28
        wave = (math.sin(self.pulse_phase) + 1) / 2          # 0 ... 1
        if self.scene is not None:
            if self.phase == "choose":
                step = int(round(wave * 5))
                if step != self.halo_step:
                    self.halo_step = step
                    for key in self.halo_keys:
                        self.place_pawn(key)
            elif self.phase == "roll" and not self.rolling[HUMAN]:
                step = 1 + int(round(wave * 4))
                if step != self.frame_step:
                    self.frame_step = step
                    self.place_frame(HUMAN)
        self.root.after(PULSE_MS, self.pulse)

    # ===== THE ANIMATION SCRIPTS (what happens on screen, step by step) =====

    # Script: a die tumbles in its frame - it spins round a random axis,
    # hopping a little, and slows down until it lies still showing the number
    # that was rolled.
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    #   value  - the number that was rolled (1 to 6)
    def tumble_die(self, player, value):
        final = resting_rotation(value, twist=self.die_twist[player])
        axis = random_axis()
        spin = random.choice((-1, 1)) * random.uniform(900, 1260)  # degrees
        self.die_value[player] = value
        self.rolling[player] = True
        self.sound.play("dice")
        self.place_frame(player)
        detail = [112]            # width of the quick pictures, in pixels

        # Turns the die a little further and lets it hop. If painting a picture
        # takes too long (a slow computer) the next ones are painted a little
        # smaller, so the die keeps turning smoothly.
        # Parameters:
        #   u - animation progress from 0.0 (start) to 1.0 (end)
        def update(u):
            eased = ease_out(u)
            turned = rot_axis(axis, spin * (1 - eased)) @ final
            started = time.perf_counter()
            picture = self.scene.die_picture(player, turned, quick=True,
                                             small=detail[0])
            cost = (time.perf_counter() - started) * 1000.0
            if cost > 24 and detail[0] > 64:
                detail[0] -= 16
            elif cost < 10 and detail[0] < 112:
                detail[0] += 8
            hop = abs(math.sin(u * math.pi * 3)) * (1 - u) * 0.16
            self.place_die(player, picture, hop)

        yield from self.tween(DIE_SECONDS, update)
        self.rolling[player] = False
        self.place_frame(player)
        self.place_die(player)

    # Script: one token jumps to a neighbouring square in an arc.
    # Parameters:
    #   key    - which pawn: a (player, token index) pair
    #   target - the slot (x, y, scale) the token jumps to
    #   height - how high the arc goes, in pixels
    def hop(self, key, target, height):
        entry = self.display[key]
        x0, y0, _, scale0 = entry

        # Puts the token on its arc for this moment of the hop.
        # Parameters:
        #   u - animation progress from 0.0 (start) to 1.0 (end)
        def update(u):
            eased = ease_in_out(u)
            entry[0] = x0 + (target.x - x0) * eased
            entry[1] = y0 + (target.y - y0) * eased
            entry[2] = height * 4 * u * (1 - u)         # a parabola
            entry[3] = scale0 + (target.scale - scale0) * eased
            self.place_pawn(key)

        yield from self.tween(HOP_SECONDS, update)
        entry[2] = 0.0
        self.place_pawn(key)
        self.sound.play("hop")

    # Script: a burst on the landing square while every captured token flies
    # back to its yard in a high arc.
    # Parameters:
    #   mover            - player whose token captured
    #   landing_progress - progress of the square where it landed
    #   victims          - keys of the captured pawns
    def capture_effect(self, mover, landing_progress, victims):
        row, column = cell_of_progress(mover, landing_progress)
        starts = {key: list(self.display[key]) for key in victims}
        homes = {key: yard_slot(*key) for key in victims}
        for key in victims:
            self.raise_pawn(key)
        self.sound.play("capture")

        # Moves the captured tokens along their arc and draws the burst.
        # Parameters:
        #   u - animation progress from 0.0 (start) to 1.0 (end)
        def update(u):
            eased = ease_in_out(u)
            for key in victims:
                x0, y0, _, scale0 = starts[key]
                home, entry = homes[key], self.display[key]
                entry[0] = x0 + (home.x - x0) * eased
                entry[1] = y0 + (home.y - y0) * eased
                entry[2] = FLY_HEIGHT * 4 * u * (1 - u)
                entry[3] = scale0 + (home.scale - scale0) * eased
                self.place_pawn(key)
            x, y = self.scene.grid_pos(column + 0.5, row + 0.5)
            self.show("boom", self.scene.boom_picture(u), x, y)

        yield from self.tween(FLY_SECONDS, update)
        self.hide("boom")
        for key in victims:
            self.display[key][2] = 0.0
            self.place_pawn(key)
            self.landing.pop(key[0], None)          # that token is gone
            self.place_marker(key[0])

    # Script: after a move, tokens that now share a square (or that stopped
    # sharing one) slide to their proper places.
    def settle(self):
        layout = resting_layout(self.state)
        starts = {key: list(entry) for key, entry in self.display.items()}
        moving = [key for key, slot in layout.items()
                  if abs(self.display[key][0] - slot.x) > 0.01
                  or abs(self.display[key][1] - slot.y) > 0.01
                  or abs(self.display[key][3] - slot.scale) > 0.01]
        if not moving:
            return

        # Moves the tokens a little closer to their places.
        # Parameters:
        #   u - animation progress from 0.0 (start) to 1.0 (end)
        def update(u):
            eased = ease_in_out(u)
            for key in moving:
                slot, entry = layout[key], self.display[key]
                x0, y0, _, scale0 = starts[key]
                entry[0] = x0 + (slot.x - x0) * eased
                entry[1] = y0 + (slot.y - y0) * eased
                entry[2] = 0.0
                entry[3] = scale0 + (slot.scale - scale0) * eased
                self.place_pawn(key)

        yield from self.tween(SETTLE_SECONDS, update)

    # Script: plays one whole move. The rules (self.state) are updated at once;
    # then the token hops square by square, a capture bursts and sends the
    # victims home, and crowded squares are tidied up.
    # Parameters:
    #   state       - the current GameState (token positions and whose turn it
    #                 is)
    #   token_index - which token of the player moves (0 or 1)
    #   dice        - the number rolled on the die (1 to 6)
    def move_script(self, state, token_index, dice):
        player = state.current_player
        opponent = 1 - player
        key = (player, token_index)
        start = state.tokens[player][token_index]
        end = destination(start, dice)
        new_state = apply_move(state, token_index, dice)
        victims = [(opponent, index) for index, (old, new) in enumerate(
                       zip(state.tokens[opponent], new_state.tokens[opponent]))
                   if old != START and new == START]
        self.state = new_state
        self.raise_pawn(key)

        yield from self.wait(LEAD_SECONDS)
        for progress in range(start + 1, end + 1):          # one hop a square
            height = LONG_HOP_HEIGHT if progress - 1 == START else HOP_HEIGHT
            target = square_slot(player, token_index, progress)
            yield from self.hop(key, target, height)
            yield from self.wait(REST_SECONDS)
        self.landing[player] = end
        self.place_marker(player)
        if end == FINISH:
            self.sound.play("home")               # the token reached the centre
        if victims:
            yield from self.capture_effect(player, end, victims)
        yield from self.settle()
        self.refresh_scores()

    # Script: the person's die tumbles; then the tokens that can move start to
    # glow and the token buttons appear.
    def human_roll_script(self):
        dice = roll_dice()
        self.set_status("Rolling...", "", HUMAN_INK)
        yield from self.tumble_die(HUMAN, dice)
        self.dice = dice
        self.add_log(HUMAN, f"{self.player_name} rolled {dice}")
        self.phase = "choose"
        self.halo_keys = {(HUMAN, index)
                          for index in get_legal_moves(self.state)}
        for key in self.halo_keys:
            self.place_pawn(key)
        self.refresh_controls()
        self.set_status(f"{self.player_name} rolled a {dice}",
                        "Click a glowing token, press its button, or key "
                        "1 / 2.", HUMAN_INK, die=(HUMAN, dice))

    # Script: plays the person's move, then (unless the game is over) the AI's
    # whole turn, and finally hands the turn back.
    # Parameters:
    #   state       - the current GameState (token positions and whose turn it
    #                 is)
    #   token_index - which token of the player moves (0 or 1)
    #   dice        - the number rolled on the die (1 to 6)
    def human_move_script(self, state, token_index, dice):
        self.set_status(f"{self.your_word()} Move", "", HUMAN_INK, die=(HUMAN, dice))
        yield from self.move_script(state, token_index, dice)
        if get_winner(self.state) is None:
            yield from self.wait(GAP_SECONDS)
            yield from self.ai_turn_script()
        if self.finish_turn() == HUMAN:
            yield from self.confetti()

    # Script: the AI plays the first move of a game it was chosen to start.
    def ai_opening_script(self):
        yield from self.wait(0.5)
        yield from self.ai_turn_script()
        self.finish_turn()

    # Script: the computer's whole turn. It rolls, searches with expectiminimax
    # (ai.py) to pick the token closest to victory, shows what it worked out,
    # and then moves.
    def ai_turn_script(self):
        state = self.state
        depth, mistake_chance = DIFFICULTY[self.difficulty]
        self.set_status("AI's Turn", "The computer is thinking...", AI_INK)
        self.root.update_idletasks()
        dice = roll_dice()
        best_token, values = choose_best_move(state, dice, depth,
                                              mistake_chance=mistake_chance)
        yield from self.tumble_die(AI, dice)
        self.set_status(f"The AI rolled a {dice}", "", AI_INK, die=(AI, dice))

        rows = []
        for token_index, value in values.items():
            start = state.tokens[AI][token_index]
            rows.append((f"Token {token_index + 1}",
                         f"{position_text(start)} → "
                         f"{position_text(destination(start, dice))}",
                         f"{value:+.2f}", token_index == best_token))
        self.show_thinking(dice, depth, rows)
        self.add_log(AI, f"AI rolled {dice} and "
                         f"{describe_move(state, best_token, dice)}")
        yield from self.wait(AFTER_DIE_SECONDS)
        yield from self.move_script(state, best_token, dice)

    # Script: coloured paper falls over the window when you win.
    def confetti(self):
        canvas = self.canvas
        width, height = self.size
        k = self.scene.k
        pieces = [{"x": random.uniform(0.03, 0.97) * width,
                   "start": random.uniform(0.0, 1.3),     # seconds until it appears
                   "vx": random.uniform(-70, 70) * k,
                   "vy": random.uniform(120, 300) * k,
                   "half": random.uniform(4, 8) * k,
                   "turn": random.uniform(0, 6.28),
                   "spin": random.uniform(-9, 9),
                   "colour": random.choice(CONFETTI_COLOURS)}
                  for _ in range(110)]

        # Draws one picture of the falling paper.
        # Parameters:
        #   u - animation progress from 0.0 (start) to 1.0 (end)
        def update(u):
            canvas.delete("confetti")
            seconds = u * CONFETTI_SECONDS
            for piece in pieces:
                fall = seconds - piece["start"]
                if fall < 0:
                    continue
                x = piece["x"] + piece["vx"] * fall
                y = -20 * k + piece["vy"] * fall + 260 * k * fall ** 2
                if y > height + 20 * k:
                    continue
                angle = piece["turn"] + piece["spin"] * fall
                half = piece["half"]
                cos, sin = math.cos(angle), math.sin(angle)
                corners = []
                for dx, dy in ((-half, -half * 0.6), (half, -half * 0.6),
                               (half, half * 0.6), (-half, half * 0.6)):
                    corners += [x + dx * cos - dy * sin, y + dx * sin + dy * cos]
                canvas.create_polygon(corners, fill=piece["colour"],
                                      outline="", tags=("fx", "confetti"))

        yield from self.tween(CONFETTI_SECONDS, update)
        canvas.delete("confetti")

    # ===== THE GAME FLOW =====

    # Called when all the animation of a turn is over: either hands the dice
    # back to the person, or announces the winner and updates the scoreboard.
    # Returns the winner (HUMAN or AI), or None if the game goes on.
    def finish_turn(self):
        winner = get_winner(self.state)
        if winner is None:
            self.phase = "roll"
            self.set_status(f"{self.your_word()} Turn", "Click your die, press ROLL DICE, "
                            "or press Space.", HUMAN_INK)
        else:
            self.scores[winner] += 1
            self.phase = "over"
            self.sound.play("win" if winner == HUMAN else "lose")
            if winner == HUMAN:
                you = self.player_name == "You"
                self.set_status("You Win!" if you else f"{self.player_name} Wins!",
                                "All the red tokens reached the centre.",
                                HUMAN_INK)
                self.add_log(HUMAN, ("You win!" if you else
                                     f"{self.player_name} wins!")
                             + " All the red tokens are home.")
            else:
                self.set_status("The AI Wins", "Try again, or lower the "
                                "difficulty.", AI_INK)
                self.add_log(AI, "The AI wins this time.")
        self.trim_caches()
        self.refresh_scores()
        self.place_frame(HUMAN)
        self.refresh_controls()
        return winner

    # In a very long session the token buttons and texts of the panel would
    # fill the memory with pictures that are never needed again. When there are
    # too many, they are thrown away and the window is drawn again.
    def trim_caches(self):
        if self.scene is None or len(self.photos) < MAX_PHOTOS:
            return
        self.scene.cache = {key: picture
                            for key, picture in self.scene.cache.items()
                            if key[0] not in ("tokbtn", "text")}
        self.photos, self.shown = {}, {}
        self.refresh_all()

    # Resets everything for a fresh game (the NEW GAME button, key N, or PLAY
    # AGAIN). If the AI was chosen to start, it plays at once.
    def start_new_game(self):
        self.cancel_script()
        first = AI if self.first_player == "AI" else HUMAN
        self.state = new_game(first)
        self.dice = None
        self.landing = {}
        self.halo_keys = set()
        self.rolling = {HUMAN: False, AI: False}
        self.die_value = {HUMAN: None, AI: None}     # nobody has rolled yet
        self.display = {key: [slot.x, slot.y, 0.0, slot.scale]
                        for key, slot in resting_layout(self.state).items()}
        self.canvas.delete("fx")
        if self.scene is not None:
            self.hide("boom")
        self.clear_log()
        self.show_thinking(None, 0, [])
        if first == AI:
            self.add_log(None, "New game: the AI starts.")
        elif self.player_name == "You":
            self.add_log(None, "New game: you start.")
        else:
            self.add_log(None, f"New game: {self.player_name} starts.")
        if first == AI:
            self.phase = "busy"
            self.set_status("AI's Turn", "The computer starts this game.",
                            AI_INK)
            self.refresh_all()
            self.run(self.ai_opening_script())
        else:
            self.finish_turn()
            self.refresh_all()


# ===== 4. START THE PROGRAM =====

# Opens the game window and keeps it running until it is closed.
def main():
    enable_sharp_text()
    try:
        root = tk.Tk()
    except tk.TclError as error:
        print("Ludo Duel could not open a window:", error)
        return
    LudoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
