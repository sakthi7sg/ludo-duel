# Name:       SELVARAJ SAKTHIVEL
# Student ID: 3607YZMI
# Module:     5FTC2067 Artificial Intelligence Principles - Mini Project
# File:       ui_start.py
# Game:       Ludo Duel - the start page of the desktop window

from PIL import ImageDraw

import ui_art
from ui_art import AI, HUMAN, MUTED, SIDE, TEXT, GOLD
from ui_kit import draw_text, get_font, put

PAGE_W, PAGE_H = ui_art.DESIGN_W, ui_art.DESIGN_H

# Where things go on the page, in design units.
LOGO_TOP = 36.0
LOGO_SCALE = 1.3
TAGLINE_Y = 226.0
CARD_W, CARD_H, CARD_TOP = 400.0, 250.0, 270.0
CARD_GAP = 120.0                                   # space for the VS badge
CARD_LEFT = {HUMAN: 640.0 - CARD_GAP / 2 - CARD_W, AI: 640.0 + CARD_GAP / 2}
BUTTON_BOX = (495.0, 566.0, 290.0, 68.0)           # (x, y, width, height)
HINT_Y = 660.0
FOOTER_BOX = (290.0, 706.0, 700.0, 50.0)

LINE = (58, 86, 142)                               # thin divider lines

# What each profile card says: label, name, then rows of (label, value).
PROFILE = {
    HUMAN: ("PLAYER 1", "You", (("Colour", "Red"),
                                ("Starts in", "Top-right yard"),
                                ("Controls", "Mouse or keys 1 · 2"))),
    AI: ("PLAYER 2", "AI", (("Colour", "Blue"),
                            ("Starts in", "Bottom-left yard"),
                            ("Strategy", "Expectiminimax search"))),
}


# Works out the scale and the offset that centre the page in the window.
# Returns (k, left, top): pixels per design unit and the page's top-left corner.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
def page_geometry(width, height):
    k = min(width / PAGE_W, height / PAGE_H)
    return k, (width - PAGE_W * k) / 2.0, (height - PAGE_H * k) / 2.0


# Paints one player's profile card: avatar, label and name, the two tokens,
# a divider and three rows of facts. Returns an RGBA image.
# Parameters:
#   player    - the player number (HUMAN = red, AI = blue)
#   k         - scale factor: pixels per design unit
#   show_name - True to show the player's name row
def _profile_card(player, k, show_name=True):
    w, h = int(CARD_W * k), int(CARD_H * k)
    side = SIDE[player]
    card = ui_art.render_card(w, h, k, glow=side["mid"], radius=16.0)
    pad = 26 * k
    label, name, rows = PROFILE[player]
    if not show_name:
        name = ""

    avatar = ui_art.badge(int(54 * k), player)
    put(card, avatar, pad, pad)
    x = pad + 54 * k + 16 * k
    draw_text(card, x, pad + 13 * k, label, get_font("semibold", 12.5 * k),
              MUTED, spacing=2.4 * k)
    if name:
        draw_text(card, x, pad + 39 * k, name, get_font("bold", 27 * k), TEXT)

    radius = 15 * k                                   # the two tokens, top right
    for number in (1, 2):
        pawn = ui_art.render_pawn(player, number, radius)
        cx = w - pad - radius - (2 - number) * (radius * 2 + 10 * k)
        put(card, pawn, cx - pawn.width / 2, pad + 27 * k - pawn.height / 2)

    draw = ImageDraw.Draw(card)
    top = 104 * k
    draw.line((pad, top, w - pad, top), fill=LINE + (255,), width=max(1, int(k)))
    label_font, value_font = get_font("regular", 14 * k), get_font("semibold", 14 * k)
    for index, (key, value) in enumerate(rows):
        y = top + (32 + index * 38) * k
        draw_text(card, pad, y, key, label_font, MUTED)
        colour = side["text"] if index == 0 else TEXT
        draw_text(card, w - pad, y, value, value_font, colour, align="r")
        if index < len(rows) - 1:
            line_y = y + 19 * k
            draw.line((pad, line_y, w - pad, line_y), fill=LINE + (120,),
                      width=max(1, int(k)))
    # a thin coloured bar along the top edge marks the side
    bar = int(3 * k)
    draw.rounded_rectangle((pad, 0, w - pad, bar), radius=bar / 2,
                           fill=side["mid"] + (255,))
    return card


# Paints the round VS badge between the two cards. Returns an RGBA image.
# Parameters:
#   k - scale factor: pixels per design unit
def _vs_badge(k):
    size = int(66 * k)
    badge = ui_art.render_card(size, size, k, radius=33.0)
    draw_text(badge, size / 2, size / 2, "VS", get_font("extrabold", 22 * k),
              GOLD, align="m")
    return badge


# Paints the whole start page, without the button (the button changes when
# the mouse is over it, so it is a separate picture: see render_start_button).
# Returns an RGB image of the window's size.
# Parameters:
#   width    - width in pixels
#   height   - height in pixels
#   student  - (name, student ID, module, project) shown on the card
#   name_box - True to leave room for the name entry box
def render_start_page(width, height, student, name_box=False):
    name, student_id, module, project = student
    k, left, top = page_geometry(width, height)
    page = ui_art.render_background(width, height).convert("RGBA")

    logo = ui_art.render_logo(k * LOGO_SCALE)
    put(page, logo, (width - logo.width) / 2, top + LOGO_TOP * k)
    draw_text(page, width / 2, top + TAGLINE_Y * k,
              "A two-player game of chance against an AI opponent",
              get_font("regular", 18 * k), (196, 210, 236), align="m")

    for player in (HUMAN, AI):
        card = _profile_card(player, k, show_name=not (name_box and player == HUMAN))
        put(page, card, left + CARD_LEFT[player] * k, top + CARD_TOP * k)
    vs = _vs_badge(k)
    put(page, vs, width / 2 - vs.width / 2,
        top + (CARD_TOP + CARD_H / 2) * k - vs.height / 2)

    draw_text(page, width / 2, top + HINT_Y * k, "Press Enter to start",
              get_font("regular", 13 * k), MUTED, align="m")

    # footer: the student details on one quiet line between two dividers
    x, y, w, h = FOOTER_BOX
    draw = ImageDraw.Draw(page)
    x1, x2 = left + x * k, left + (x + w) * k
    draw.line((x1, top + y * k, x2, top + y * k), fill=LINE + (255,),
              width=max(1, int(k)))
    footer = f"{name}   |   Student ID {student_id}   |   {module} {project}"
    draw_text(page, width / 2, top + (y + h / 2 + 2) * k, footer,
              get_font("medium", 13.5 * k), (176, 192, 224), align="m",
              spacing=0.4 * k)
    return page.convert("RGB")


# Where the name box for Player 1 goes on the start page. Returns
# (x, y, width, height) in pixels.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
def name_box_region(width, height):
    k, left, top = page_geometry(width, height)
    x = CARD_LEFT[HUMAN] + 26.0 + 54.0 + 14.0
    y = CARD_TOP + 26.0 + 22.0
    return (left + x * k, top + y * k, 196.0 * k, 36.0 * k)


# Paints the green START GAME button in one state ("normal", "hover" or
# "press"). Returns (picture, x, y): the picture and where its top-left corner
# goes.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
#   state  - "normal", "hover" or "pressed"
def render_start_button(width, height, state="normal"):
    k, left, top = page_geometry(width, height)
    x, y, w, h = BUTTON_BOX
    picture = ui_art.render_button("green", w * k, h * k, k, "START GAME",
                                   state=state, icon=ui_art.icon_play)
    pad = int(0.35 * int(h * k))                    # the button's glow margin
    return picture, left + x * k - pad, top + y * k - pad


# The area of the window where a click starts the game. Returns (x1, y1, x2, y2)
# in pixels.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
def start_button_region(width, height):
    k, left, top = page_geometry(width, height)
    x, y, w, h = BUTTON_BOX
    return (left + x * k, top + y * k, left + (x + w) * k, top + (y + h) * k)
