# Name:       SELVARAJ SAKTHIVEL
# Student ID: 3607YZMI
# Module:     5FTC2067 Artificial Intelligence Principles - Mini Project
# File:       ui_art.py
# Game:       Ludo Duel - all the pictures of the desktop window
#
# This file PAINTS the game window with Pillow. It does not react to the mouse
# and does not know the rules. It makes the dark background, the board
# (squares, stars, home columns, yards, centre triangles), glossy pawns with
# shadows and "you can move me" rings, the dice frames (the 3-D dice come from
# ui_dice.py), the LUDO DUEL logo, glass cards, buttons, tabs and icons.
# ludo_main_gui.py asks for these pictures and puts them on a Tkinter canvas.
#
# DESIGN UNITS ("du"): the layout is drawn on an imaginary window of 1280 x 794
# du and scaled by k (pixels per du), so the game looks the same on a small
# laptop and on a big screen. Sizes are in du unless the text says "px".
# SMOOTH EDGES: shapes are drawn 3-4 times larger and shrunk again
# ("supersampling"). Gradients come from ui_kit.py.

import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import ui_kit
from ui_dice import FRONT_LIGHT, Die, resting_rotation
from ui_kit import (draw_text, finish, get_font, glow_from_mask,
                    gradient_image, mix, put, radial_gradient_image,
                    rounded_mask, shape_mask, star_points, text_width,
                    through_mask)

HUMAN = 0
AI = 1

# ===== 1. COLOURS =====
WHITE = (255, 255, 255)
TEXT = (238, 244, 255)               # normal text on the dark window
MUTED = (150, 170, 208)              # quieter text
GOLD = (255, 190, 4)
GOLD_LIGHT = (255, 214, 64)
GOLD_DARK = (230, 150, 0)
INK = (58, 36, 6)                    # dark brown text on gold
GREEN = (30, 205, 100)

# Pawn and yard colours of the two sides: light, middle, dark.
SIDE = {
    HUMAN: {"light": (255, 138, 126), "mid": (232, 36, 38),
            "dark": (150, 12, 22), "text": (255, 120, 112),
            "plate_top": (252, 230, 234), "plate_bottom": (233, 174, 186),
            "yard_a": (216, 30, 34), "yard_b": (160, 8, 20),
            "label": (176, 22, 32)},
    AI: {"light": (150, 200, 255), "mid": (28, 108, 240),
         "dark": (8, 42, 150), "text": (110, 190, 255),
         "plate_top": (222, 238, 254), "plate_bottom": (158, 196, 250),
         "yard_a": (6, 84, 216), "yard_b": (0, 44, 148),
         "label": (20, 62, 168)},
}

CELL_TOP = (240, 244, 251)           # white squares of the track
CELL_BOTTOM = (212, 223, 241)
STAR_GREY = (108, 119, 142)

# ===== 2. LAYOUT (in design units) =====
DESIGN_W, DESIGN_H = 1280, 794

BOARD_X, BOARD_Y, CELL = 101.0, 112.0, 41.6      # top-left of the board, square size

PANEL_X1, PANEL_X2 = 789.0, 1268.0
CARDS = {                                          # (x1, y1, x2, y2)
    "student": (PANEL_X1, 20.0, PANEL_X2, 88.0),
    "settings": (PANEL_X1, 103.0, PANEL_X2, 264.0),
    "status": (PANEL_X1, 280.0, PANEL_X2, 437.0),
    "score": (PANEL_X1, 452.0, PANEL_X2, 538.0),
    "tabs": (PANEL_X1, 555.0, PANEL_X2, 772.0),
}
TAB_HEIGHT = 44.0                                  # height of the tab row

# Segmented controls: (x, y, width, height) and their options.
SEGMENTS = {
    "difficulty": {"box": (813.0, 142.0, 224.0, 28.0),
                   "options": ("Easy", "Medium", "Hard")},
    "first": {"box": (1078.0, 142.0, 174.0, 28.0),
              "options": ("You", "AI")},
    "speed": {"box": (813.0, 224.0, 197.0, 28.0),
              "options": ("Normal", "Fast")},
}
NEW_GAME_BOX = (1054.0, 201.0, 199.0, 49.0)        # (x, y, width, height)
ROLL_BOX = (831.0, 361.0, 397.0, 57.0)
TOKEN_BOXES = ((831.0, 361.0, 195.0, 57.0), (1033.0, 361.0, 195.0, 57.0))

# The middle of the little die on the status card (in du).
STATUS_DIE_CENTRE = (832.0, 316.0)

# Where the tabs sit: name -> (x offset inside the card, width).
TABS = (("Game Log", 11.0, 141.0), ("AI Thinking", 156.0, 170.0),
        ("Rules", 330.0, 138.0))

# The log / thinking / rules area (x1, y1, x2, y2).
PAGE_BOX = (PANEL_X1 + 14.0, 559.0 + TAB_HEIGHT + 12.0,
            PANEL_X2 - 14.0, 772.0 - 12.0)

# Dice frames and captions. Positions are in squares of the board
# (counted from its top-left corner), sizes in squares.
DIE_FRAME_SIZE = 3.55
DIE_CENTRE = {HUMAN: (2.49, 3.05), AI: (12.18, 12.76)}
CAPTION_CENTRE = {HUMAN: (2.55, 5.30), AI: (12.14, 10.34)}
CAPTION_SIZE = {HUMAN: (2.8, 0.62), AI: (2.9, 0.66)}
CAPTION_TEXT = {HUMAN: "YOUR DIE", AI: "AI'S DIE"}

# How big the pawns are, in squares: radius on the track and the scale
# factors the game uses (yard pawns are bigger than track pawns).
PAWN_RADIUS = 0.40


# Converts a layout rectangle given in design units into pixels. Returns (x1,
# y1, x2, y2) in pixels, rounded to whole numbers.
# Parameters:
#   box   - rectangle (x1, y1, x2, y2) in design units
#   k     - scale factor: pixels per design unit
#   shift - (dx, dy) offset in pixels added after scaling
def du_box(box, k, shift=(0, 0)):
    x1, y1, x2, y2 = box
    return (int(round(x1 * k + shift[0])), int(round(y1 * k + shift[1])),
            int(round(x2 * k + shift[0])), int(round(y2 * k + shift[1])))


# ===== 3. THE BACKGROUND =====

# Paints the window background: a deep navy blue with soft diagonal streaks of
# light on the left and a red glow at the bottom right. Returns an RGB image.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
def render_background(width, height):
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]
    scale = float(max(width, height))
    top = np.array((3.0, 11.0, 32.0), dtype=np.float32)
    bottom = np.array((8.0, 24.0, 60.0), dtype=np.float32)
    colour = top + (bottom - top) * (y ** 1.4)[..., None]
    colour = np.broadcast_to(colour, (height, width, 3)).copy()

    # a soft lighter area behind the board
    spot = np.exp(-(((x - 0.30) / 0.42) ** 2 + ((y - 0.55) / 0.55) ** 2))
    colour += spot[..., None] * np.array((0.0, 9.0, 24.0), dtype=np.float32)

    # Adds one soft, bright diagonal line of light to the background.
    # Parameters:
    #   x0        - start x as a fraction of the width
    #   y0        - start y as a fraction of the height
    #   x1        - end x as a fraction of the width
    #   y1        - end y as a fraction of the height
    #   thickness - width of the line
    #   tint      - colour of the light
    #   strength  - how strong the effect is (0..1)
    def streak(x0, y0, x1, y1, thickness, tint, strength):
        px, py = x * width, y * height
        ax, ay = x0 * width, y0 * height
        bx, by = x1 * width, y1 * height
        dx, dy = bx - ax, by - ay
        length = max(dx * dx + dy * dy, 1.0)
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / length, 0.0, 1.0)
        distance = np.sqrt((px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2)
        fade = np.exp(-(distance / (thickness * scale)) ** 2)
        along = np.maximum(np.sin(np.pi * t), 0.0) ** 0.6
        colour[...] += (fade * along * strength)[..., None] * np.array(
            tint, dtype=np.float32)

    streak(-0.02, 0.24, 0.08, 0.06, 0.012, (0, 60, 150), 0.85)
    streak(-0.02, 0.33, 0.06, 0.18, 0.006, (30, 110, 230), 0.6)
    streak(-0.02, 0.70, 0.07, 0.44, 0.010, (0, 50, 130), 0.55)
    streak(-0.02, 0.98, 0.10, 0.80, 0.014, (0, 70, 170), 0.55)
    streak(0.52, 1.03, 0.66, 0.94, 0.010, (190, 28, 52), 0.75)
    streak(0.55, 1.03, 0.74, 0.90, 0.020, (120, 20, 44), 0.45)
    streak(0.97, 0.10, 1.03, 0.02, 0.012, (0, 50, 130), 0.5)

    # a faint dark edge (vignette)
    edge = ((x - 0.5) ** 2 + (y - 0.5) ** 2) * 0.55
    colour *= (1.0 - edge[..., None])
    return Image.fromarray(np.clip(colour, 0, 255).astype(np.uint8), "RGB")


# ===== 4. GLASS CARDS =====

# Paints one glass-like card of the right-hand panel: a dark blue body, a
# bright thin border, a soft inner glow and an optional coloured glow in the
# bottom-left corner or a sheen in the top-right corner. Returns an RGBA image
# of the given size.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
#   k      - scale factor: pixels per design unit
#   glow   - colour of the corner glow, or None
#   sheen  - True to add a light sheen in the top-right corner
#   radius - corner radius in design units
def render_card(width, height, k, glow=None, sheen=False, radius=13.0):
    w, h = int(width), int(height)
    r = radius * k
    outer = rounded_mask(w, h, r)
    border = max(1.6, 1.7 * k)
    inner = Image.new("L", (w, h), 0)
    inner.paste(rounded_mask(int(w - 2 * border), int(h - 2 * border),
                             max(1.0, r - border)),
                (int(border), int(border)))

    body = gradient_image(w, h, [(0.0, (16, 34, 70)), (0.55, (9, 23, 50)),
                                 (1.0, (6, 17, 40))], 90)
    diagonal = gradient_image(w, h, [(0.0, (60, 110, 200, 46)),
                                     (0.5, (40, 80, 160, 10)),
                                     (1.0, (20, 40, 100, 0))], 35)
    body.alpha_composite(diagonal)

    if sheen:                                   # curved light, top right
        layer = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(layer)
        draw.ellipse((w * 0.55, -h * 1.25, w * 1.35, h * 0.55), fill=70)
        layer = layer.filter(ImageFilter.GaussianBlur(h * 0.06))
        tint = Image.new("RGBA", (w, h), (70, 130, 255, 0))
        tint.putalpha(layer)
        body.alpha_composite(tint)
    if glow is not None:                        # coloured corner glow
        layer = radial_gradient_image(
            w, h, (0, h), h * 1.25,
            [(0.0, glow + (150,)), (0.45, glow + (45,)), (1.0, glow + (0,))],
            squash=0.55)
        body.alpha_composite(layer)

    card = through_mask(body, inner)
    rim = gradient_image(w, h, [(0.0, (176, 224, 255, 255)),
                                (0.10, (96, 154, 245, 250)),
                                (0.6, (58, 108, 214, 240)),
                                (1.0, (48, 94, 196, 240))], 90)
    ring = ImageChops.subtract(outer, inner)
    result = through_mask(rim, ring)
    if glow is not None:                        # border picks up the glow
        corner = radial_gradient_image(
            w, h, (0, h), h * 1.1,
            [(0.0, glow + (255,)), (0.5, glow + (90,)), (1.0, glow + (0,))],
            squash=0.55)
        result.alpha_composite(through_mask(corner, ring))

    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    base.alpha_composite(card)
    base.alpha_composite(result)
    # a soft blue glow just inside the border
    soft = ImageChops.subtract(inner, inner.filter(
        ImageFilter.GaussianBlur(max(2.0, 5 * k))))
    glow_layer = Image.new("RGBA", (w, h), (40, 110, 255, 0))
    glow_layer.putalpha(soft.point(lambda v: int(v * 0.35)))
    base.alpha_composite(glow_layer)
    return base


# ===== 5. ICONS =====

# Starts a new supersampled drawing for an icon. Returns (image, draw, unit)
# where unit = pixels of the big drawing per 1/100 of the icon width (so shapes
# can be written in 0..100).
# Parameters:
#   size - width and height in pixels
#   ss   - supersampling factor (drawn this many times bigger, then shrunk)
def icon_canvas(size, ss=4):
    big = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    return big, ImageDraw.Draw(big), size * ss / 100.0


# A person (round head and shoulders) inside a thin circle, like an account
# picture. Returns an RGBA image.
# Parameters:
#   size   - width and height in pixels
#   colour - colour as an (r, g, b) tuple
#   ring   - True to draw a circle round the person
def icon_user(size, colour, ring=True):
    big, draw, u = icon_canvas(size)
    c = colour + (255,)
    if ring:
        draw.ellipse((5 * u, 5 * u, 95 * u, 95 * u), outline=c, width=int(5 * u))
    clip = Image.new("L", big.size, 0)
    ImageDraw.Draw(clip).ellipse((8 * u, 8 * u, 92 * u, 92 * u), fill=255)
    person = Image.new("RGBA", big.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(person)
    pd.ellipse((34 * u, 22 * u, 66 * u, 54 * u), fill=c)
    pd.ellipse((20 * u, 58 * u, 80 * u, 118 * u), fill=c)
    person.putalpha(ImageChops.multiply(person.getchannel("A"), clip))
    big.alpha_composite(person)
    return finish(big, 4)


# A cog wheel (for "AI difficulty"). Returns an RGBA image.
# Parameters:
#   size   - width and height in pixels
#   colour - colour as an (r, g, b) tuple
def icon_gear(size, colour):
    big, draw, u = icon_canvas(size)
    c = colour + (255,)
    for number in range(8):
        angle = math.radians(number * 45)
        x, y = 50 + 36 * math.cos(angle), 50 + 36 * math.sin(angle)
        turn = angle + math.pi / 2
        corners = [(x + dx * math.cos(turn) - dy * math.sin(turn),
                    y + dx * math.sin(turn) + dy * math.cos(turn))
                   for dx, dy in ((-9, -12), (9, -12), (9, 12), (-9, 12))]
        draw.polygon([(px * u, py * u) for px, py in corners], fill=c)
    draw.ellipse((17 * u, 17 * u, 83 * u, 83 * u), fill=c)
    return finish(_punch(big, (36 * u, 36 * u, 64 * u, 64 * u)), 4)


# Makes an oval area of a picture see-through (used for the hole of the gear).
# Returns the picture (changed).
# Parameters:
#   picture - a PIL RGBA image
#   box     - oval area (x1, y1, x2, y2) to make see-through
def _punch(picture, box):
    hole = Image.new("L", picture.size, 255)
    ImageDraw.Draw(hole).ellipse(box, fill=0)
    picture.putalpha(ImageChops.multiply(picture.getchannel("A"), hole))
    return picture


# A speed dial (for "animation speed"). Returns an RGBA image.
# Parameters:
#   size   - width and height in pixels
#   colour - colour as an (r, g, b) tuple
def icon_gauge(size, colour):
    big, draw, u = icon_canvas(size)
    c = colour + (255,)
    draw.arc((8 * u, 14 * u, 92 * u, 98 * u), 180, 360, fill=c, width=int(9 * u))
    for degrees in (200, 235, 270, 305, 340):
        a = math.radians(degrees)
        draw.line((50 * u + 28 * u * math.cos(a), 56 * u + 28 * u * math.sin(a),
                   50 * u + 38 * u * math.cos(a), 56 * u + 38 * u * math.sin(a)),
                  fill=c, width=int(5 * u))
    a = math.radians(305)
    draw.line((50 * u, 58 * u, 50 * u + 30 * u * math.cos(a),
               58 * u + 30 * u * math.sin(a)), fill=c, width=int(8 * u))
    draw.ellipse((40 * u, 48 * u, 60 * u, 68 * u), fill=c)
    return finish(big, 4)


# Two people (for "who starts next"). Returns an RGBA image.
# Parameters:
#   size   - width and height in pixels
#   colour - colour as an (r, g, b) tuple
def icon_people(size, colour):
    big, draw, u = icon_canvas(size)
    c = colour + (255,)
    dim = mix(colour, (20, 40, 90), 0.35) + (255,)
    draw.ellipse((52 * u, 16 * u, 78 * u, 42 * u), fill=dim)
    draw.pieslice((40 * u, 46 * u, 92 * u, 98 * u), 180, 360, fill=dim)
    draw.ellipse((22 * u, 12 * u, 52 * u, 42 * u), fill=c)
    draw.pieslice((6 * u, 48 * u, 68 * u, 110 * u), 180, 360, fill=c)
    return finish(big, 4)


# A brain (for "AI thinking"). Returns an RGBA image.
# Parameters:
#   size   - width and height in pixels
#   colour - colour as an (r, g, b) tuple
def icon_brain(size, colour):
    big, draw, u = icon_canvas(size)
    c = colour + (255,)
    for cx, cy, r in ((34, 36, 22), (66, 36, 22), (28, 60, 21), (72, 60, 21),
                      (50, 44, 24), (42, 74, 20), (58, 74, 20)):
        draw.ellipse(((cx - r) * u, (cy - r) * u, (cx + r) * u, (cy + r) * u),
                     fill=c)
    return finish(_carve(big, [(50, 22), (50, 92)], 5 * u), 4)


# Cuts see-through lines into a picture (the centre line and the folds of the
# brain). Returns the picture (changed).
# Parameters:
#   picture - a PIL RGBA image
#   points  - line points in 0..100 icon units
#   width   - thickness of the cut line in pixels
def _carve(picture, points, width):
    scale = picture.width / 100.0
    cut = Image.new("L", picture.size, 255)
    draw = ImageDraw.Draw(cut)
    draw.line([(x * scale, y * scale) for x, y in points], fill=0,
              width=int(width))
    for folds in (((26, 40), (38, 46), (34, 58)), ((74, 40), (62, 46), (66, 58)),
                  ((24, 66), (36, 70), (42, 62)), ((76, 66), (64, 70), (58, 62))):
        draw.line([(x * scale, y * scale) for x, y in folds], fill=0,
                  width=int(width * 0.8), joint="curve")
    picture.putalpha(ImageChops.multiply(picture.getchannel("A"), cut))
    return picture


# An open book (for "Rules"). Returns an RGBA image.
# Parameters:
#   size   - width and height in pixels
#   colour - colour as an (r, g, b) tuple
def icon_book(size, colour):
    big, draw, u = icon_canvas(size)
    c = colour + (255,)
    draw.rounded_rectangle((8 * u, 18 * u, 48 * u, 84 * u), radius=5 * u,
                           outline=c, width=int(7 * u))
    draw.rounded_rectangle((52 * u, 18 * u, 92 * u, 84 * u), radius=5 * u,
                           outline=c, width=int(7 * u))
    for y in (38, 54):
        draw.line((17 * u, y * u, 39 * u, y * u), fill=c, width=int(6 * u))
        draw.line((61 * u, y * u, 83 * u, y * u), fill=c, width=int(6 * u))
    return finish(big, 4)


# A play triangle (for NEW GAME). Returns an RGBA image.
# Parameters:
#   size   - width and height in pixels
#   colour - colour as an (r, g, b) tuple
def icon_play(size, colour):
    big, draw, u = icon_canvas(size)
    draw.polygon([(22 * u, 10 * u), (22 * u, 90 * u), (88 * u, 50 * u)],
                 fill=colour + (255,))
    return finish(big, 4)


# A small flat die icon: rounded square with five dots. Returns an RGBA image.
# Parameters:
#   size - width and height in pixels
#   body - colour of the die
#   pip  - colour of the dots
#   tilt - rotation of the die in degrees
def icon_die(size, body, pip, tilt=0.0):
    ss = 4
    big = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    u = size * ss / 100.0
    square = Image.new("RGBA", big.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(square)
    draw.rounded_rectangle((12 * u, 12 * u, 88 * u, 88 * u), radius=20 * u,
                           fill=body + (255,))
    shade = gradient_image(big.width, big.height,
                           [(0.0, (255, 255, 255, 60)), (1.0, (0, 0, 0, 40))],
                           60)
    square.alpha_composite(through_mask(shade, square.getchannel("A")))
    draw = ImageDraw.Draw(square)
    for x, y in ((31, 31), (69, 31), (50, 50), (31, 69), (69, 69)):
        draw.ellipse(((x - 8) * u, (y - 8) * u, (x + 8) * u, (y + 8) * u),
                     fill=pip + (255,))
    if tilt:
        square = square.rotate(tilt, resample=Image.BICUBIC)
    big.alpha_composite(square)
    return finish(big, ss)


# A small rounded badge with a symbol, used in the scoreboard: a red square
# with a person (you) or a blue circle with a gear (the AI). Returns an RGBA
# image.
# Parameters:
#   size   - width and height in pixels
#   player - the player number (HUMAN = red, AI = blue)
def badge(size, player):
    ss = 4
    big = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    u = size * ss / 100.0
    side = SIDE[player]
    mask = Image.new("L", big.size, 0)
    md = ImageDraw.Draw(mask)
    if player == HUMAN:
        md.rounded_rectangle((4 * u, 4 * u, 96 * u, 96 * u), radius=24 * u, fill=255)
    else:
        md.ellipse((4 * u, 4 * u, 96 * u, 96 * u), fill=255)
    fill = gradient_image(big.width, big.height,
                          [(0.0, side["light"]), (0.45, side["mid"]),
                           (1.0, side["dark"])], 80)
    base = through_mask(fill, mask)
    big.alpha_composite(base)
    rim = ImageChops.subtract(mask, mask.filter(
        ImageFilter.GaussianBlur(2.2 * u)).point(lambda v: 255 if v > 200 else 0))
    edge = Image.new("RGBA", big.size, (255, 255, 255, 0))
    edge.putalpha(rim.point(lambda v: int(v * 0.55)))
    big.alpha_composite(edge)
    small = finish(big, ss)
    if player == HUMAN:
        person = icon_user(int(size * 0.74), (255, 214, 208), ring=False)
    else:
        person = icon_gear(int(size * 0.62), (205, 232, 255))
    small.alpha_composite(person, ((size - person.width) // 2,
                                   (size - person.height) // 2 + int(size * 0.03)))
    return small


# ===== 6. BOARD GEOMETRY (which square of the 15 x 15 grid is which) =====
# The board is a 15 x 15 grid (rows and columns counted from 0, top-left
# first): four 6 x 6 corners, a 3 x 3 centre and four arms. Only two corners
# are yards (red top-right, blue bottom-left); the other two corners hold the
# two dice.
#
# Grid cell (row, column) of every ring square, in the order the tokens
# travel (clockwise). Ring square 0 is red's START, 26 is blue's START.
RING_CELLS = (
    [(1, 8), (2, 8), (3, 8), (4, 8), (5, 8)]            # down the top arm
    + [(6, col) for col in range(9, 15)]                 # right arm, top row
    + [(7, 14)]                                          # right tip
    + [(8, col) for col in range(14, 8, -1)]             # right arm, bottom
    + [(row, 8) for row in range(9, 15)]                 # down the bottom arm
    + [(14, 7)]                                          # bottom tip
    + [(row, 6) for row in range(14, 8, -1)]             # up the bottom arm
    + [(8, col) for col in range(5, -1, -1)]             # left arm, bottom
    + [(7, 0)]                                           # left tip
    + [(6, col) for col in range(0, 6)]                  # left arm, top row
    + [(row, 6) for row in range(5, -1, -1)]             # up the top arm
    + [(0, 7), (0, 8)]                                   # top tip and corner
)

# The five home-column squares of each player, from the outside inwards.
HOME_COLUMN_CELLS = {
    HUMAN: [(1, 7), (2, 7), (3, 7), (4, 7), (5, 7)],      # down the top arm
    AI: [(13, 7), (12, 7), (11, 7), (10, 7), (9, 7)],     # up the bottom arm
}

# The two yards: (player, first row, first column).
YARD_ORIGIN = {HUMAN: (0, 9), AI: (9, 0)}

# Ring squares that are START squares (they get the player's colour).
START_SQUARES = {0: HUMAN, 26: AI}


# Where a token waits inside its yard, in squares from the board's top-left
# corner (tokens sit in rows of two on the plate). Returns (x, y) of the middle
# of the spot, in squares.
# Parameters:
#   player            - the player number (HUMAN = red, AI = blue)
#   index             - which token (0 or 1)
#   tokens_per_player - how many tokens each player has
def yard_slot_cell(player, index, tokens_per_player):
    row, column = YARD_ORIGIN[player]
    lines = (tokens_per_player + 1) // 2
    line, place = divmod(index, 2)
    in_line = min(2, tokens_per_player - 2 * line)
    x = column + 3.0 + (place - (in_line - 1) / 2) * 1.6
    y = row + 3.35 + (line - (lines - 1) / 2) * 1.2
    return x, y


# ===== 7. PAINTING THE BOARD =====

# Paints one square of the track: a slightly glossy tile, optionally with a
# star on it. Returns an RGBA image.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
#   top    - colour at the top of the tile
#   bottom - colour at the bottom
#   star   - colour of the star, or None for no star
#   edge   - True to draw a light top edge and dark bottom edge
def tile_image(width, height, top, bottom, star=None, edge=True):
    tile = gradient_image(width, height, [(0.0, top), (1.0, bottom)], 90)
    draw = ImageDraw.Draw(tile)
    if edge:
        light = mix(top, (255, 255, 255), 0.55)
        dark = mix(bottom, (0, 0, 30), 0.30)
        draw.line((0, 0, width, 0), fill=light + (255,))
        draw.line((0, height - 1, width, height - 1), fill=dark + (255,))
    if star is not None:
        ss = 4
        layer = Image.new("RGBA", (width * ss, height * ss), (0, 0, 0, 0))
        outer = min(width, height) * 0.31 * ss
        ImageDraw.Draw(layer).polygon(
            star_points(width * ss / 2, height * ss / 2 + outer * 0.04,
                        outer, outer * 0.47), fill=star + (255,))
        tile.alpha_composite(finish(layer, ss))
    return tile


# Paints the whole board: its shadow and rim, the track squares with the stars,
# the two coloured home columns, the triangles in the middle, and the two yards
# with their plates, labels and the empty places for the tokens. Returns
# (image, margin): an RGBA image and the number of pixels of free space around
# the 15 x 15 grid inside it (for the shadow).
# Parameters:
#   cell              - size of one board square in pixels
#   safe_squares      - ring squares that get a star
#   tokens_per_player - how many tokens each player has
def render_board(cell, safe_squares, tokens_per_player):
    c = float(cell)
    margin = int(round(c * 0.8))
    size = int(round(15 * c)) + 2 * margin
    ss = 3

    # --- the outline of the board (cross + two yards, rounded corners) ----
    arm_round, yard_round = 0.30 * c, 0.64 * c

    # Pixel rectangle of a block of grid squares on the (enlarged) drawing.
    # Returns (x1, y1, x2, y2) in pixels.
    # Parameters:
    #   col0 - left column
    #   row0 - top row
    #   col1 - right column
    #   row1 - bottom row
    #   s    - supersampling factor
    def box(col0, row0, col1, row1, s):
        return (int((margin + col0 * c) * s), int((margin + row0 * c) * s),
                int((margin + col1 * c) * s) - 1,
                int((margin + row1 * c) * s) - 1)

    # Draws the white silhouette of the board: the cross-shaped track and the
    # two yards, with rounded outer corners.
    # Parameters:
    #   draw - the ImageDraw object of the mask
    #   s    - supersampling factor
    def paint(draw, s):
        draw.rounded_rectangle(box(6, 0, 9, 15, s), radius=arm_round * s,
                               fill=255, corners=(True, False, True, False))
        draw.rounded_rectangle(box(0, 6, 15, 9, s), radius=arm_round * s,
                               fill=255, corners=(True, False, True, False))
        draw.rounded_rectangle(box(9, 0, 15, 6, s), radius=yard_round * s,
                               fill=255, corners=(False, True, False, False))
        draw.rounded_rectangle(box(0, 9, 6, 15, s), radius=yard_round * s,
                               fill=255, corners=(False, False, False, True))

    raw = shape_mask(size, size, paint, ss)
    outline = raw.filter(ImageFilter.GaussianBlur(0.14 * c)).point(
        lambda v: max(0, min(255, int((v - 128) * 6 + 128))))

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ui_kit.drop_shadow(canvas, outline, 0, 0, 0.30 * c, (0, 0.16 * c), 200)
    ui_kit.drop_shadow(canvas, outline, 0, 0, 0.07 * c, (0, 0.03 * c), 150)
    rim_width = max(2.0, 0.075 * c)
    rim_mask = outline.filter(ImageFilter.GaussianBlur(rim_width * 0.75)).point(
        lambda v: min(255, int(v * 5)))
    rim_fill = gradient_image(size, size, [(0.0, (112, 142, 205)),
                                           (0.5, (52, 74, 130)),
                                           (1.0, (30, 44, 88))], 90)
    canvas.alpha_composite(through_mask(rim_fill, rim_mask))
    base_fill = gradient_image(size, size, [(0.0, (22, 34, 62)),
                                            (1.0, (10, 20, 44))], 90)
    canvas.alpha_composite(through_mask(base_fill, outline))

    # --- everything inside the outline is drawn on one layer ---------------
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gap = max(1, int(round(0.045 * c)))

    # Pixel position of a line of the grid (rounded, so neighbouring squares
    # always touch without a gap). Returns a whole number of pixels.
    # Parameters:
    #   index - grid line number (0 to 15)
    def edge(index):
        return int(round(margin + index * c))

    tiles = {}

    # Gives the picture of a track square (made once per kind). Returns an RGBA
    # image.
    # Parameters:
    #   kind - tile type ("white", "star", "red", "blue")
    #   w    - tile width in pixels
    #   h    - tile height in pixels
    def tile_for(kind, w, h):
        key = (kind, w, h)
        if key not in tiles:
            if kind == "white":
                tiles[key] = tile_image(w, h, CELL_TOP, CELL_BOTTOM)
            elif kind == "star":
                tiles[key] = tile_image(w, h, CELL_TOP, CELL_BOTTOM, STAR_GREY)
            else:
                side = HUMAN if kind.startswith("red") else AI
                top = mix(SIDE[side]["light"], SIDE[side]["mid"], 0.55)
                bottom = mix(SIDE[side]["mid"], SIDE[side]["dark"], 0.35)
                star = WHITE if kind.endswith("star") else None
                tiles[key] = tile_image(w, h, top, bottom, star)
        return tiles[key]

    # Puts one tile on a square of the grid.
    # Parameters:
    #   row  - grid row
    #   col  - grid column
    #   kind - tile type
    def lay_tile(row, col, kind):
        x0, y0 = edge(col) + gap // 2, edge(row) + gap // 2
        x1, y1 = edge(col + 1) - (gap - gap // 2), edge(row + 1) - (gap - gap // 2)
        layer.alpha_composite(tile_for(kind, x1 - x0, y1 - y0), (x0, y0))

    for ring_index, (row, col) in enumerate(RING_CELLS):
        if ring_index in START_SQUARES:
            kind = "red_star" if START_SQUARES[ring_index] == HUMAN else "blue_star"
        elif ring_index in safe_squares:
            kind = "star"
        else:
            kind = "white"
        lay_tile(row, col, kind)
    for player, name in ((HUMAN, "red"), (AI, "blue")):
        for row, col in HOME_COLUMN_CELLS[player]:
            lay_tile(row, col, name)

    # --- the two triangles in the middle ---------------------------------
    for player, up in ((HUMAN, False), (AI, True)):
        side = SIDE[player]
        left, right = margin + 6 * c + gap, margin + 9 * c - gap
        apex = (margin + 7.5 * c, margin + 7.5 * c + (0.05 * c if up else -0.05 * c))
        base_y = margin + (9 * c - gap if up else 6 * c + gap)
        points = [(left, base_y), (right, base_y), apex]
        triangle = shape_mask(size, size, lambda draw, s: draw.polygon(
            [(x * s, y * s) for x, y in points], fill=255), ss)
        paint_stops = [(0.0, side["light"]), (0.5, side["mid"]), (1.0, side["dark"])]
        fill = gradient_image(size, size, paint_stops, 270 if up else 90)
        layer.alpha_composite(through_mask(fill, triangle))
        line = ImageChops.subtract(triangle, triangle.filter(
            ImageFilter.GaussianBlur(1.0)).point(lambda v: 255 if v > 235 else 0))
        glint = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        glint.putalpha(line.point(lambda v: int(v * 0.45)))
        layer.alpha_composite(glint)

    # --- the yards -------------------------------------------------------
    for player, (row0, col0) in YARD_ORIGIN.items():
        _paint_yard(layer, player, row0, col0, c, margin, gap, tokens_per_player,
                    edge)

    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), outline))
    canvas.alpha_composite(layer)
    return canvas, margin


# Paints one yard: the big coloured square with a glassy shine, the light plate
# in the middle, its label (PLAYER 1 / 2) and the round places where the tokens
# wait.
# Parameters:
#   layer             - the board picture to paint on
#   player            - the player number (HUMAN = red, AI = blue)
#   row0              - top row of the yard on the grid
#   col0              - left column of the yard on the grid
#   c                 - size of one square in pixels
#   margin            - free space round the grid in pixels
#   gap               - gap between tiles in pixels
#   tokens_per_player - how many tokens each player has
#   edge              - function giving the pixel edge of a grid line
def _paint_yard(layer, player, row0, col0, c, margin, gap, tokens_per_player,
                edge):
    side = SIDE[player]
    x0, y0 = edge(col0) + gap // 2, edge(row0) + gap // 2
    x1, y1 = edge(col0 + 6) - gap // 2, edge(row0 + 6) - gap // 2
    w, h = x1 - x0, y1 - y0
    body = gradient_image(w, h, [(0.0, side["yard_a"]), (1.0, side["yard_b"])], 55)
    shine = gradient_image(w, h, [(0.0, (255, 255, 255, 46)),
                                  (0.22, (255, 255, 255, 8)),
                                  (1.0, (255, 255, 255, 0))], 90)
    body.alpha_composite(shine)
    glow = radial_gradient_image(w, h, (w * 0.3, h * 0.2), w * 0.8,
                                 [(0.0, (255, 255, 255, 22)),
                                  (1.0, (255, 255, 255, 0))])
    body.alpha_composite(glow)
    layer.alpha_composite(body, (x0, y0))

    # the plate
    px0, py0 = edge(col0 + 1), edge(row0 + 1)
    pw = edge(col0 + 5) - px0
    ph = edge(row0 + 5) - py0
    groove_pad = 0.11 * c
    groove = rounded_mask(pw + 2 * groove_pad, ph + 2 * groove_pad, 0.66 * c)
    groove_fill = gradient_image(groove.width, groove.height,
                                 [(0.0, mix(side["yard_b"], (0, 0, 0), 0.35)),
                                  (1.0, mix(side["yard_a"], (255, 255, 255), 0.18))],
                                 90)
    layer.alpha_composite(through_mask(groove_fill, groove),
                          (int(px0 - groove_pad), int(py0 - groove_pad)))
    plate_mask = rounded_mask(pw, ph, 0.55 * c)
    plate = gradient_image(pw, ph, [(0.0, side["plate_top"]),
                                    (1.0, side["plate_bottom"])], 90)
    inner_edge = gradient_image(pw, ph, [(0.0, (0, 0, 0, 38)),
                                         (0.10, (0, 0, 0, 0)),
                                         (1.0, (0, 0, 0, 0))], 90)
    plate.alpha_composite(inner_edge)
    layer.alpha_composite(through_mask(plate, plate_mask), (px0, py0))

    # the round places where the tokens wait
    for index in range(tokens_per_player):
        sx, sy = yard_slot_cell(player, index, tokens_per_player)
        cx, cy = margin + sx * c, margin + sy * c
        radius = 0.50 * c
        dent = radial_gradient_image(
            int(radius * 2 + 4), int(radius * 2 + 4),
            (radius + 2, radius + 2), radius,
            [(0.0, (0, 0, 0, 34)), (0.8, (0, 0, 0, 26)), (1.0, (0, 0, 0, 0))])
        layer.alpha_composite(dent, (int(cx - radius - 2), int(cy - radius - 2)))

    # the label: PLAYER 1 (YOU), upright, or PLAYER 2 (AI), leaning
    label = ("PLAYER 1  (YOU)", "PLAYER 2 (AI)")[player]
    font = get_font(("extrabold", "bolditalic")[player], 0.42 * c)
    draw_text(layer, margin + (col0 + 3.0) * c, margin + (row0 + 1.92) * c,
              label, font, side["label"], align="m", valign="c",
              shadow=(0, 0.04 * c, 0.03 * c, (255, 255, 255, 120)))


# ===== 8. PAWNS, SHADOWS AND SELECTION RINGS =====

# A big-picture mask of a filled circle. Returns an "L" image.
# Parameters:
#   size   - width and height in pixels
#   cx     - centre x in pixels
#   cy     - centre y in pixels
#   radius - radius in pixels
def _disc_mask(size, cx, cy, radius):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((cx - radius, cy - radius, cx + radius,
                                  cy + radius), fill=255)
    return mask


# Paints one glossy pawn: a round button with a bright rim, a deeper centre, a
# shine and the token number. Returns an RGBA image (about 2.6 radii wide).
# Parameters:
#   player - the player number (HUMAN = red, AI = blue)
#   number - token number shown on the pawn (1 or 2)
#   radius - radius of the pawn in pixels
def render_pawn(player, number, radius):
    side = SIDE[player]
    ss = 4
    pad = max(3, int(radius * 0.18))
    size = int(math.ceil(radius * 2)) + 2 * pad
    big = size * ss
    cx = cy = big / 2
    r = radius * ss
    canvas = Image.new("RGBA", (big, big), (0, 0, 0, 0))

    # thickness: a darker disc a little lower than the top
    lower = gradient_image(big, big, [(0.0, mix(side["dark"], (0, 0, 0), 0.25)),
                                      (1.0, mix(side["dark"], (0, 0, 0), 0.55))], 90)
    canvas.alpha_composite(through_mask(lower, _disc_mask(big, cx, cy + 0.10 * r,
                                                          r * 0.985)))
    # the rim
    rim = gradient_image(big, big, [(0.0, mix(side["light"], WHITE, 0.45)),
                                    (0.45, side["light"]),
                                    (1.0, mix(side["mid"], side["dark"], 0.4))], 60)
    canvas.alpha_composite(through_mask(rim, _disc_mask(big, cx, cy - 0.02 * r, r)))
    # the groove between rim and centre
    groove = Image.new("RGBA", (big, big), side["dark"] + (255,))
    canvas.alpha_composite(through_mask(groove, _disc_mask(big, cx, cy, r * 0.835)))
    # the centre of the button
    centre = radial_gradient_image(
        big, big, (cx - 0.28 * r, cy - 0.36 * r), r * 1.32,
        [(0.0, mix(side["light"], side["mid"], 0.45)),
         (0.45, side["mid"]), (1.0, side["dark"])])
    canvas.alpha_composite(through_mask(centre, _disc_mask(big, cx, cy, r * 0.775)))
    # the shine
    shine_mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(shine_mask).ellipse((cx - 0.58 * r, cy - 0.90 * r,
                                        cx + 0.58 * r, cy - 0.12 * r), fill=255)
    shine_mask = ImageChops.multiply(shine_mask,
                                     _disc_mask(big, cx, cy, r * 0.93))
    shine = gradient_image(big, big, [(0.0, (255, 255, 255, 140)),
                                      (0.55, (255, 255, 255, 30)),
                                      (1.0, (255, 255, 255, 0))], 90)
    canvas.alpha_composite(through_mask(shine, shine_mask))
    pawn = finish(canvas, ss)

    font = get_font("extrabold", radius * 1.12)
    draw_text(pawn, size / 2, size / 2 + radius * 0.02, str(number), font, WHITE,
              align="m", valign="c",
              shadow=(0, radius * 0.07, radius * 0.06,
                      mix(side["dark"], (0, 0, 0), 0.5) + (190,)))
    return pawn


# Paints the soft dark ellipse a pawn casts on the board. Returns an RGBA
# image.
# Parameters:
#   radius - radius in pixels
#   amount - darkness of the shadow (1.0 = pawn on the board)
def render_shadow(radius, amount=1.0):
    rx, ry = radius * 0.95 * amount, radius * 0.42 * amount
    blur = max(1.0, radius * 0.16)
    width, height = int(rx * 2 + blur * 6), int(ry * 2 + blur * 6)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).ellipse((width / 2 - rx, height / 2 - ry,
                                  width / 2 + rx, height / 2 + ry), fill=255)
    return glow_from_mask(mask, (0, 0, 10), blur, 0.62 * (0.4 + 0.6 * amount))


# Paints the golden ring that shows which pawns can be moved. Returns an RGBA
# image (the ring is centred in it).
# Parameters:
#   radius - radius in pixels
#   grow   - how far the ring has grown (0..1, for the pulse)
def render_halo(radius, grow):
    ring_radius = radius * (1.16 + 0.20 * grow)
    thick = max(2.0, radius * 0.11)
    size = int(ring_radius * 2 + radius * 1.4)
    ss = 3
    mask = Image.new("L", (size * ss, size * ss), 0)
    c = size * ss / 2
    ImageDraw.Draw(mask).ellipse(
        (c - ring_radius * ss, c - ring_radius * ss,
         c + ring_radius * ss, c + ring_radius * ss), outline=255,
        width=int(thick * ss))
    mask = mask.resize((size, size), Image.LANCZOS)
    glow = glow_from_mask(mask, GOLD, radius * 0.22, 1.5)
    ring = Image.new("RGBA", (size, size), mix(GOLD_LIGHT, WHITE, 0.3) + (255,))
    ring.putalpha(mask)
    glow.alpha_composite(ring)
    return glow


# ===== 9. DICE FRAMES AND CAPTIONS =====
FRAME_COLOUR = {HUMAN: (255, 196, 40), AI: (70, 200, 255)}


# Paints the glowing rounded frame the die sits in (gold for you, cyan for the
# AI): a dark inside, a bright thin border and a soft glow. Returns an RGBA
# image, larger than `size` by a margin of 0.3 * size on every side (for the
# glow); the frame is in the middle.
# Parameters:
#   size   - width and height in pixels
#   player - the player number (HUMAN = red, AI = blue)
#   level  - glow strength (0.0 dim to 1.0 bright)
def render_die_frame(size, player, level):
    accent = FRAME_COLOUR[player]
    margin = int(size * 0.30)
    total = size + 2 * margin
    radius = size * 0.20
    border = max(2.0, size * 0.018)
    frame = rounded_mask(size, size, radius)
    inner = Image.new("L", (size, size), 0)
    inner.paste(rounded_mask(int(size - 2 * border), int(size - 2 * border),
                             radius - border), (int(border), int(border)))
    ring = ImageChops.subtract(frame, inner)

    canvas = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    wide = Image.new("L", (total, total), 0)
    wide.paste(ring, (margin, margin))
    for blur, strength in ((size * 0.10, 0.9), (size * 0.035, 0.9)):
        canvas.alpha_composite(glow_from_mask(
            wide, accent, blur, (0.45 + 0.9 * level) * strength))

    interior = radial_gradient_image(size, size, (size * 0.5, size * 0.42),
                                     size * 0.75,
                                     [(0.0, (3, 6, 20)), (0.6, (6, 12, 32)),
                                      (1.0, (13, 24, 52))])
    shade = gradient_image(size, size, [(0.0, (0, 0, 0, 90)),
                                        (0.35, (0, 0, 0, 0)),
                                        (1.0, (0, 0, 0, 0))], 90)
    interior.alpha_composite(shade)
    canvas.alpha_composite(through_mask(interior, inner), (margin, margin))
    core = mix(accent, WHITE, 0.55)
    edge = gradient_image(size, size, [(0.0, core), (1.0, accent)], 90)
    canvas.alpha_composite(through_mask(edge, ring), (margin, margin))
    return canvas


# Paints the soft dark patch under a die inside its frame. Returns an RGBA
# image.
# Parameters:
#   width - width in pixels
def render_floor_shadow(width):
    height = int(width * 0.34)
    pad = int(width * 0.25)
    mask = Image.new("L", (width + 2 * pad, height + 2 * pad), 0)
    ImageDraw.Draw(mask).ellipse((pad, pad, pad + width, pad + height), fill=255)
    return glow_from_mask(mask, (0, 0, 6), width * 0.07, 0.9)


# Paints the small label under or over a die ("YOUR DIE", "AI'S DIE"). Returns
# an RGBA image.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
#   player - the player number (HUMAN = red, AI = blue)
#   k      - scale factor: pixels per design unit
def render_caption(width, height, player, k):
    w, h = int(width), int(height)
    shape = rounded_mask(w, h, h * 0.32)
    if player == HUMAN:
        fill = gradient_image(w, h, [(0.0, (172, 30, 36)), (1.0, (98, 12, 20))], 90)
        line, ink = (214, 70, 70), WHITE
    else:
        fill = gradient_image(w, h, [(0.0, (22, 58, 124)), (1.0, (10, 30, 78))], 90)
        line, ink = (72, 142, 232), (214, 232, 255)
    result = through_mask(fill, shape)
    inner = Image.new("L", (w, h), 0)
    inner.paste(rounded_mask(w - 2, h - 2, h * 0.32 - 1), (1, 1))
    outline = through_mask(Image.new("RGBA", (w, h), line + (210,)),
                           ImageChops.subtract(shape, inner))
    result.alpha_composite(outline)
    draw_text(result, w / 2, h / 2 + h * 0.02, CAPTION_TEXT[player],
              get_font("extrabold", h * 0.56), ink, align="m", valign="c",
              spacing=0.3 * k, shadow=(0, 1 * k, 1.0 * k, (0, 0, 0, 150)))
    return result


# ===== 10. THE LOGO =====
LOGO_BOX = (56.0, 2.0, 350.0, 128.0)       # where the logo goes (du)


# Paints a word as thick 3-D letters: a dark side that sticks out to the lower
# right, a glossy gradient face, a bright top edge and a soft shadow. Returns
# the width of the word in pixels.
# Parameters:
#   canvas - the picture to draw on
#   x      - left of the word in pixels
#   base   - baseline of the letters in pixels
#   word   - the word to draw
#   font   - the PIL font used for the text
#   face   - gradient stops of the letter fronts
#   side   - colour of the 3-D sides
#   depth  - how far the 3-D sides stick out, in pixels
#   glow   - colour of the glow, or None for no glow
def _extruded_text(canvas, x, base, word, font, face, side, depth, glow=None):
    width = int(text_width(word, font)) + int(depth * 2) + 8
    height = int(font.size * 1.6)
    top = base - font.size * 1.15
    mask = Image.new("L", (width, height), 0)
    pad = 4
    ImageDraw.Draw(mask).text((pad, font.size * 1.15), word, font=font,
                              fill=255, anchor="ls")
    outline = Image.new("L", (width, height), 0)
    ImageDraw.Draw(outline).text((pad, font.size * 1.15), word, font=font,
                                 fill=255, anchor="ls",
                                 stroke_width=max(1, int(depth * 0.28)))

    word_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    steps = max(2, int(depth))
    for step in range(steps, 0, -1):                 # the thick side
        shifted = ImageChops.offset(outline, int(step * 0.5), step)
        shade = mix(side, (0, 0, 0), 0.25 * (step / steps))
        word_layer.alpha_composite(through_mask(
            Image.new("RGBA", (width, height), shade + (255,)), shifted))
    word_layer.alpha_composite(through_mask(
        Image.new("RGBA", (width, height), mix(side, (0, 0, 0), 0.45) + (255,)),
        outline))
    front = gradient_image(width, height, face, 90)
    word_layer.alpha_composite(through_mask(front, mask))
    lip = ImageChops.subtract(mask, ImageChops.offset(mask, 0, max(1, int(depth * 0.35))))
    shine = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    shine.putalpha(lip.point(lambda v: int(v * 0.8)))
    word_layer.alpha_composite(shine)

    footprint = ImageChops.lighter(outline, ImageChops.offset(outline, int(depth * 0.5), int(depth)))
    ui_kit.drop_shadow(canvas, footprint, int(x - pad), int(top), depth * 1.3,
                       (0, depth * 1.4), 170)
    if glow is not None:
        halo = Image.new("L", (width + 40, height + 40), 0)
        halo.paste(footprint, (20, 20))
        put(canvas, glow_from_mask(halo, glow, depth * 2.0, 0.65),
            x - pad - 20, top - 20)
    put(canvas, word_layer, x - pad, top)
    return text_width(word, font)


# Paints the LUDO DUEL logo: a red and a blue die above the words LUDO (white)
# and DUEL (blue) in thick leaning letters, with a golden swoosh underneath.
# Returns an RGBA image (LOGO_BOX in size).
# Parameters:
#   k - scale factor: pixels per design unit
def render_logo(k):
    x1, y1, x2, y2 = LOGO_BOX
    w, h = int((x2 - x1) * k), int((y2 - y1) * k)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # letters: the capitals should be about 33 du tall
    sample = get_font("blackitalic", 100)
    size = 33.0 / (ui_kit.cap_height(sample) / 100.0) * k
    font = get_font("blackitalic", size)
    base = 103.0 * k - y1 * k
    start = 9.0 * k
    gap = size * 0.30
    depth = max(3.0, 3.4 * k)
    first = _extruded_text(
        canvas, start, base, "LUDO", font,
        [(0.0, (255, 255, 255)), (0.55, (226, 234, 248)), (1.0, (150, 168, 204))],
        (54, 70, 110), depth)
    _extruded_text(
        canvas, start + first + gap, base, "DUEL", font,
        [(0.0, (122, 204, 255)), (0.5, (30, 130, 255)), (1.0, (8, 70, 214))],
        (6, 38, 140), depth, glow=(30, 120, 255))

    # the golden swoosh
    swoosh = Image.new("L", (w, h), 0)
    ss = 3
    big = Image.new("L", (w * ss, h * ss), 0)
    draw = ImageDraw.Draw(big)
    left, right = 10.0 * k, 285.0 * k
    top_y = base + 0.46 * size
    upper, lower = [], []
    for step in range(81):
        t = step / 80.0
        px = left + (right - left) * t
        py = top_y - 9.0 * k * (1.0 - (1.0 - t) ** 2.0) + 0.0
        thick = (0.4 + 2.4 * math.sin(math.pi * min(1.0, t ** 0.5))) * k * 1.9
        upper.append((px * ss, (py - thick / 2) * ss))
        lower.append((px * ss, (py + thick / 2) * ss))
    draw.polygon(upper + lower[::-1], fill=255)
    swoosh = big.resize((w, h), Image.LANCZOS)
    paint = gradient_image(w, h, [(0.0, (255, 120, 20, 255)),
                                  (0.35, (255, 196, 40, 255)),
                                  (0.8, (255, 214, 90, 150)),
                                  (1.0, (255, 214, 90, 0))], 0)
    put(canvas, glow_from_mask(swoosh, (255, 150, 20), 5 * k, 1.1), 0, 0)
    put(canvas, through_mask(paint, swoosh), 0, 0)

    # the two dice
    red = Die((226, 38, 42), (255, 255, 255), shine=0.5)
    blue = Die((30, 112, 242), (255, 255, 255), shine=0.5)
    red_size, blue_size = int(86 * k), int(63 * k)
    red_sprite = red.render(resting_rotation(5, twist=-14, tilt=(28, -32)), red_size)
    blue_sprite = blue.render(resting_rotation(4, twist=12, tilt=(30, -30)), blue_size)
    put(canvas, red_sprite, (170 - x1) * k - red_size / 2, (36 - y1) * k - red_size / 2)
    put(canvas, blue_sprite, (227 - x1) * k - blue_size / 2, (40 - y1) * k - blue_size / 2)
    return canvas


# ===== 11. CONTROLS: SEGMENTS, BUTTONS, TABS, PANELS =====

# Chooses the biggest size (not above `size`) at which a text still fits into a
# width. Returns an ImageFont.
# Parameters:
#   weight    - font weight name ("regular", "bold", ...)
#   text      - the text that must fit
#   size      - largest font size to try
#   max_width - widest the text may be, in pixels
def fit_font(weight, text, size, max_width):
    current = size
    while current > size * 0.6:
        font = get_font(weight, current)
        if text_width(text, font) <= max_width:
            return font
        current -= 0.5
    return get_font(weight, size * 0.6)


# Paints a text on a see-through picture (used for every text that changes
# while the game runs). Returns an RGBA image.
# Parameters:
#   width   - width in pixels
#   height  - height in pixels
#   text    - the text to show
#   weight  - font weight name ("regular", "bold", ...)
#   size    - font size in pixels
#   colour  - colour as an (r, g, b) tuple
#   align   - horizontal alignment: "l" left, "c" centre, "r" right
#   shadow  - text shadow as (dx, dy, blur, colour), or None
#   spacing - extra space between letters in pixels
def text_picture(width, height, text, weight, size, colour, align="l",
                 shadow=None, spacing=0.0):
    picture = Image.new("RGBA", (max(1, int(width)), max(1, int(height))),
                        (0, 0, 0, 0))
    font = fit_font(weight, text, size, width)
    x = {"l": 0, "m": width / 2, "r": width}[align]
    draw_text(picture, x, height / 2, text, font, colour, align=align,
              valign="c", shadow=shadow, spacing=spacing)
    return picture


# Paints a row of choices (like "Easy | Medium | Hard") in a dark rounded bar;
# the chosen one is a glowing gold button. Returns an RGBA image.
# Parameters:
#   options  - labels of the choices
#   selected - index of the chosen option
#   width    - width in pixels
#   height   - height in pixels
#   k        - scale factor: pixels per design unit
def render_segments(options, selected, width, height, k):
    w, h = int(width), int(height)
    radius = h * 0.32
    outer = rounded_mask(w, h, radius)
    inner = Image.new("L", (w, h), 0)
    border = max(1.0, 1.2 * k)
    inner.paste(rounded_mask(int(w - 2 * border), int(h - 2 * border),
                             radius - border), (int(border), int(border)))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fill = gradient_image(w, h, [(0.0, (6, 15, 36)), (1.0, (11, 26, 58))], 90)
    canvas.alpha_composite(through_mask(fill, inner))
    line = gradient_image(w, h, [(0.0, (74, 120, 205, 255)),
                                 (1.0, (42, 82, 160, 255))], 90)
    canvas.alpha_composite(through_mask(line, ImageChops.subtract(outer, inner)))

    count = len(options)
    seg_w = (w - 2 * border) / count
    pad = max(2.0, 2.2 * k)
    for number, name in enumerate(options):
        x0 = border + number * seg_w
        if number == selected:
            sw, sh = int(seg_w - pad), int(h - 2 * border - pad)
            if sw < 4 or sh < 4:
                continue
            shape = rounded_mask(sw, sh, radius - border - pad * 0.3)
            gold = gradient_image(sw, sh, [(0.0, (255, 226, 80)),
                                           (0.5, (255, 190, 16)),
                                           (1.0, (240, 150, 0))], 90)
            gloss = gradient_image(sw, sh, [(0.0, (255, 255, 255, 90)),
                                            (0.5, (255, 255, 255, 0)),
                                            (1.0, (255, 255, 255, 0))], 90)
            gold.alpha_composite(gloss)
            px, py = int(x0 + pad / 2), int(border + pad / 2)
            pad_mask = Image.new("L", (w, h), 0)
            pad_mask.paste(shape, (px, py))
            canvas.alpha_composite(glow_from_mask(pad_mask, (255, 160, 0),
                                                  3.0 * k, 0.7))
            canvas.alpha_composite(through_mask(gold, shape), (px, py))
        colour = INK if number == selected else TEXT
        weight = "bold" if number == selected else "semibold"
        font = fit_font(weight, name, 14.4 * k, seg_w - 6 * k)
        draw_text(canvas, x0 + seg_w / 2, h / 2 + 0.3 * k, name, font, colour,
                  align="m", valign="c")
    return canvas


# Paints a big glossy button with a thick lower edge: green (NEW GAME), gold
# (ROLL DICE) or grey (not available right now). Returns an RGBA image (a
# little taller than `height`: it includes the glow round the button).
# Parameters:
#   kind   - button colour: "green", "gold" or "grey"
#   width  - width in pixels
#   height - height in pixels
#   k      - scale factor: pixels per design unit
#   text   - the text to show
#   state  - "normal", "hover", "pressed" or "disabled"
#   icon   - function that draws the icon, or None for no icon
#   ink    - text colour, or None for the default
def render_button(kind, width, height, k, text, state="normal", icon=None,
                  ink=None):
    w, h = int(width), int(height)
    depth = max(3, int(round(0.085 * h)))
    glow_pad = int(0.35 * h)
    palette = {
        "green": ([(0.0, (74, 222, 124)), (0.45, (24, 182, 82)), (1.0, (8, 138, 54))],
                  (2, 96, 36), (40, 220, 110), WHITE),
        "gold": ([(0.0, (255, 238, 104)), (0.45, (255, 200, 30)), (1.0, (250, 166, 0))],
                 (184, 112, 0), (255, 170, 20), INK),
        "off": ([(0.0, (84, 98, 136)), (1.0, (56, 68, 104))],
                (34, 44, 74), None, (156, 170, 202)),
    }[kind]
    stops, edge_colour, glow_colour, ink_default = palette
    ink = ink or ink_default
    lift = {"normal": 0, "hover": 0, "press": max(1, depth // 2)}[state]
    face_h = h - depth
    radius = min(face_h * 0.28, 18 * k)

    canvas = Image.new("RGBA", (w + 2 * glow_pad, h + 2 * glow_pad), (0, 0, 0, 0))
    face_mask = rounded_mask(w, face_h, radius)
    edge_mask = rounded_mask(w, face_h, radius)
    if glow_colour is not None:
        wide = Image.new("L", canvas.size, 0)
        wide.paste(face_mask, (glow_pad, glow_pad + depth))
        strength = 0.55 if state == "hover" else 0.38
        canvas.alpha_composite(glow_from_mask(wide, glow_colour, 0.16 * h, strength))
    edge = Image.new("RGBA", (w, face_h), edge_colour + (255,))
    canvas.alpha_composite(through_mask(edge, edge_mask),
                           (glow_pad, glow_pad + depth))
    face = gradient_image(w, face_h, stops, 90)
    if state == "hover":
        face.alpha_composite(Image.new("RGBA", (w, face_h), (255, 255, 255, 34)))
    if state == "press":
        face.alpha_composite(Image.new("RGBA", (w, face_h), (0, 0, 0, 30)))
    gloss = gradient_image(w, face_h, [(0.0, (255, 255, 255, 120)),
                                       (0.48, (255, 255, 255, 30)),
                                       (0.5, (255, 255, 255, 0)),
                                       (1.0, (255, 255, 255, 0))], 90)
    if kind != "off":
        face.alpha_composite(gloss)
    canvas.alpha_composite(through_mask(face, face_mask),
                           (glow_pad, glow_pad + lift))
    rim = ImageChops.subtract(face_mask, ImageChops.offset(face_mask, 0, 2))
    top_light = Image.new("RGBA", (w, face_h), (255, 255, 255, 0))
    top_light.putalpha(rim.point(lambda v: int(v * 0.55)))
    canvas.alpha_composite(top_light, (glow_pad, glow_pad + lift))

    # the label (icon + text, centred together)
    font = get_font("extrabold", face_h * 0.40)
    label_width = text_width(text, font, 0.5 * k)
    icon_size = int(face_h * 0.46)
    gap = 0.30 * face_h
    total = label_width + ((icon_size + gap) if icon else 0)
    left = glow_pad + (w - total) / 2
    middle = glow_pad + face_h / 2 + lift
    if icon:
        picture = icon(icon_size, ink)
        put(canvas, picture, left, middle - picture.height / 2)
        left += icon_size + gap
    shadow = ((0, 1.6 * k, 1.2 * k, (0, 0, 0, 130)) if kind == "green"
              else (0, 1.2 * k, 0.5 * k, (255, 245, 170, 140)) if kind == "gold"
              else None)
    draw_text(canvas, left, middle + 0.6 * k, text, font, ink, align="l",
              valign="c", shadow=shadow, spacing=0.5 * k)
    return canvas


# Paints a button for one pawn you can move: a dark glass button with a gold
# outline, the little pawn on the left and two lines of text. Returns an RGBA
# image.
# Parameters:
#   width    - width in pixels
#   height   - height in pixels
#   k        - scale factor: pixels per design unit
#   player   - the player number (HUMAN = red, AI = blue)
#   number   - token number shown on the button (1 or 2)
#   line_one - first line (e.g. "Token 1")
#   line_two - second line (e.g. "step 4 → step 9")
#   state    - "normal", "hover", "pressed" or "disabled"
def render_token_button(width, height, k, player, number, line_one, line_two,
                        state="normal"):
    w, h = int(width), int(height)
    pad = int(0.20 * h)
    radius = h * 0.26
    canvas = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    outer = rounded_mask(w, h, radius)
    inner = Image.new("L", (w, h), 0)
    border = max(1.5, 1.6 * k)
    inner.paste(rounded_mask(int(w - 2 * border), int(h - 2 * border),
                             radius - border), (int(border), int(border)))
    boost = {"normal": 0.0, "hover": 0.5, "press": 0.2}[state]
    wide = Image.new("L", canvas.size, 0)
    wide.paste(outer, (pad, pad))
    canvas.alpha_composite(glow_from_mask(wide, (255, 180, 20), 0.14 * h,
                                          0.25 + 0.5 * boost))
    top = mix((16, 36, 74), (40, 70, 130), boost)
    bottom = mix((8, 22, 52), (20, 44, 96), boost)
    fill = gradient_image(w, h, [(0.0, top), (1.0, bottom)], 90)
    canvas.alpha_composite(through_mask(fill, inner), (pad, pad + (2 if state == "press" else 0)))
    ring = gradient_image(w, h, [(0.0, (255, 214, 70)), (1.0, (232, 150, 0))], 90)
    canvas.alpha_composite(through_mask(ring, ImageChops.subtract(outer, inner)),
                           (pad, pad + (2 if state == "press" else 0)))
    shift = 2 if state == "press" else 0

    pawn = render_pawn(player, number, h * 0.30)
    put(canvas, pawn, pad + h * 0.12, pad + (h - pawn.height) / 2 + shift)
    text_x = pad + h * 0.12 + pawn.width + h * 0.10
    room = w - (text_x - pad) - h * 0.14
    draw_text(canvas, text_x, pad + h * 0.34 + shift, line_one,
              fit_font("bold", line_one, h * 0.30, room), TEXT, valign="c")
    draw_text(canvas, text_x, pad + h * 0.68 + shift, line_two,
              fit_font("medium", line_two, h * 0.24, room), GOLD_LIGHT, valign="c")
    return canvas


# Paints one tab above the log panel: a rounded-top button, gold when it is the
# chosen tab. Returns an RGBA image.
# Parameters:
#   width    - width in pixels
#   height   - height in pixels
#   k        - scale factor: pixels per design unit
#   label    - text on the tab
#   icon     - function that draws the icon, or None for no icon
#   selected - True if this item is the chosen one
#   hover    - True while the mouse pointer is over it
def render_tab(width, height, k, label, icon, selected, hover=False):
    w, h = int(width), int(height)
    radius = 13 * k
    outer = rounded_mask(w, h + int(radius), radius, corners=(True, True, True, True))
    outer = outer.crop((0, 0, w, h))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if selected:
        gold = gradient_image(w, h, [(0.0, (255, 226, 80)), (0.5, (255, 192, 20)),
                                     (1.0, (244, 160, 0))], 90)
        gloss = gradient_image(w, h, [(0.0, (255, 255, 255, 80)),
                                      (0.5, (255, 255, 255, 0)),
                                      (1.0, (255, 255, 255, 0))], 90)
        gold.alpha_composite(gloss)
        canvas.alpha_composite(through_mask(gold, outer))
        ink = INK
    else:
        inner = Image.new("L", (w, h), 0)
        border = max(1.2, 1.3 * k)
        inner_shape = rounded_mask(int(w - 2 * border), h + int(radius),
                                   radius - border).crop((0, 0, int(w - 2 * border),
                                                          h - int(border)))
        inner.paste(inner_shape, (int(border), int(border)))
        fill = gradient_image(w, h, [(0.0, (22, 48, 98) if hover else (15, 36, 78)),
                                     (1.0, (9, 25, 58))], 90)
        canvas.alpha_composite(through_mask(fill, inner))
        line = gradient_image(w, h, [(0.0, (90, 140, 225)), (1.0, (46, 92, 180))], 90)
        canvas.alpha_composite(through_mask(line, ImageChops.subtract(outer, inner)))
        ink = TEXT
    font = get_font("bold" if selected else "semibold", 14.0 * k)
    icon_size = int(20 * k)
    label_width = text_width(label, font)
    gap = 8 * k
    total = icon_size + gap + label_width
    left = (w - total) / 2
    picture = icon(icon_size, ink)
    put(canvas, picture, left, h / 2 - picture.height / 2 - 1.0 * k)
    draw_text(canvas, left + icon_size + gap, h / 2 - 0.6 * k, label, font, ink,
              valign="c")
    return canvas


# Paints the dark panel under the tabs that holds the log, the AI's thoughts or
# the rules: a deep blue body with a bright thin border. Returns an RGBA image.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
#   k      - scale factor: pixels per design unit
def render_panel(width, height, k):
    w, h = int(width), int(height)
    radius = 13 * k
    outer = rounded_mask(w, h, radius)
    border = max(1.4, 1.4 * k)
    inner = Image.new("L", (w, h), 0)
    inner.paste(rounded_mask(int(w - 2 * border), int(h - 2 * border),
                             radius - border), (int(border), int(border)))
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    body = gradient_image(w, h, [(0.0, (9, 28, 62)), (1.0, (4, 17, 42))], 90)
    sheen = gradient_image(w, h, [(0.0, (60, 110, 200, 34)), (1.0, (20, 40, 100, 0))], 30)
    body.alpha_composite(sheen)
    canvas.alpha_composite(through_mask(body, inner))
    line = gradient_image(w, h, [(0.0, (70, 128, 226)), (1.0, (40, 86, 176))], 90)
    canvas.alpha_composite(through_mask(line, ImageChops.subtract(outer, inner)))
    return canvas


# ===== 12. THE PAGES OF THE LOG PANEL (game log, AI thinking, rules) =====

# Paints the game log: one line per event with a coloured dot (green for game
# messages, red for you, blue for the AI). Returns an RGBA image, as tall as
# the text needs.
# Parameters:
#   entries - list of (kind, text) log lines
#   width   - page width in pixels
#   k       - scale factor: pixels per design unit
def render_log_page(entries, width, k):
    font = get_font("regular", 14.2 * k)
    line_h, gap = 19.5 * k, 8.0 * k
    indent = 22 * k
    colours = {"you": SIDE[HUMAN]["text"], "ai": SIDE[AI]["text"], "info": GREEN}
    rows = [(kind, ui_kit.wrap_text(text, font, width - indent - 6 * k))
            for kind, text in entries]
    height = int(sum(len(lines) * line_h + gap for _, lines in rows) + 8 * k)
    page = Image.new("RGBA", (int(width), max(height, 1)), (0, 0, 0, 0))
    y = 4 * k
    for kind, lines in rows:
        colour = colours.get(kind, GREEN)
        dot = icon_dot(int(11 * k), colour)
        put(page, dot, 3 * k, y + line_h / 2 - dot.height / 2)
        for number, line in enumerate(lines):
            draw_text(page, indent, y + line_h / 2 + number * line_h, line, font,
                      TEXT, valign="c")
        y += len(lines) * line_h + gap
    return page


_DOT_CACHE = {}          # dots already painted: {(size, colour): picture}


# A small glowing round dot. Returns an RGBA image.
# Parameters:
#   size   - width and height in pixels
#   colour - colour as an (r, g, b) tuple
def icon_dot(size, colour):
    key = (size, tuple(colour))
    if key in _DOT_CACHE:
        return _DOT_CACHE[key]
    ss = 4
    big = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    mask = _disc_mask(size * ss, size * ss / 2, size * ss / 2, size * ss * 0.40)
    halo = glow_from_mask(mask, colour, size * ss * 0.16, 0.8)
    big.alpha_composite(halo)
    body = radial_gradient_image(size * ss, size * ss,
                                 (size * ss * 0.42, size * ss * 0.38),
                                 size * ss * 0.5,
                                 [(0.0, mix(colour, WHITE, 0.5)),
                                  (1.0, colour)])
    big.alpha_composite(through_mask(body, mask))
    _DOT_CACHE[key] = finish(big, ss)
    return _DOT_CACHE[key]


# Paints what the AI worked out on its last turn: a short explanation and a
# table with one row per token it could move (the chosen one is gold). Returns
# an RGBA image, as tall as the content needs.
# Parameters:
#   dice  - the AI's last roll, or None before its first move
#   depth - how many moves ahead the search looks
#   rows  - list of (token, move, value, chosen) rows of the AI search
#   width - page width in pixels
#   k     - scale factor: pixels per design unit
def render_thinking_page(dice, depth, rows, width, k):
    small = get_font("regular", 13.4 * k)
    if dice is None:
        text = "Play a move and the AI's search results appear here."
        lines = ui_kit.wrap_text(text, small, width - 8 * k)
        page = Image.new("RGBA", (int(width), int(len(lines) * 19 * k + 14 * k)),
                         (0, 0, 0, 0))
        for number, line in enumerate(lines):
            draw_text(page, 4 * k, 12 * k + number * 19 * k, line, small, MUTED)
        return page
    intro = (f"The AI rolled {dice} and searched {depth} move(s) ahead. "
             f"A higher value is better for the AI.")
    lines = ui_kit.wrap_text(intro, small, width - 8 * k)
    row_h = 27 * k
    height = int(len(lines) * 19 * k + 40 * k + len(rows) * row_h + 10 * k)
    page = Image.new("RGBA", (int(width), height), (0, 0, 0, 0))
    y = 8 * k
    for line in lines:
        draw_text(page, 4 * k, y + 8 * k, line, small, MUTED)
        y += 19 * k
    y += 6 * k
    columns = (6 * k, 78 * k, width - 96 * k)
    for x, heading in zip(columns, ("TOKEN", "MOVE", "VALUE")):
        draw_text(page, x, y + 8 * k, heading, get_font("semibold", 11 * k), MUTED,
                  spacing=0.8 * k)
    y += 22 * k
    bold, normal = get_font("bold", 13.6 * k), get_font("regular", 13.6 * k)
    for token, move, value, played in rows:
        if played:
            pill = rounded_mask(int(width - 4 * k), int(row_h - 3 * k), 8 * k)
            tint = Image.new("RGBA", pill.size, GOLD + (60,))
            put(page, through_mask(tint, pill), 2 * k, y)
        font = bold if played else normal
        colour = GOLD_LIGHT if played else TEXT
        draw_text(page, columns[0], y + (row_h - 3 * k) / 2, token, font, colour)
        draw_text(page, columns[1], y + (row_h - 3 * k) / 2, move, font, colour)
        draw_text(page, columns[2], y + (row_h - 3 * k) / 2,
                  value, font, colour)
        if played:
            draw_text(page, width - 10 * k, y + (row_h - 3 * k) / 2, "PLAYED",
                      get_font("bold", 11 * k), GOLD, align="r", spacing=0.6 * k)
        y += row_h
    return page


# Paints the rules as a bullet list. Returns an RGBA image, as tall as the text
# needs.
# Parameters:
#   items - list of rule sentences
#   width - page width in pixels
#   k     - scale factor: pixels per design unit
def render_rules_page(items, width, k):
    font = get_font("regular", 13.6 * k)
    line_h, gap, indent = 19 * k, 7 * k, 20 * k
    rows = [ui_kit.wrap_text(text, font, width - indent - 6 * k) for text in items]
    height = int(sum(len(lines) * line_h + gap for lines in rows) + 10 * k)
    page = Image.new("RGBA", (int(width), height), (0, 0, 0, 0))
    y = 6 * k
    for lines in rows:
        dot = icon_dot(int(9 * k), GOLD)
        put(page, dot, 4 * k, y + line_h / 2 - dot.height / 2)
        for number, line in enumerate(lines):
            draw_text(page, indent, y + line_h / 2 + number * line_h, line, font,
                      TEXT, valign="c")
        y += len(lines) * line_h + gap
    return page


# 12b. EFFECTS ON THE BOARD (landing frame, capture burst, window icon)
BOOM_STEPS = 10                  # how many different pictures a burst has


# Paints the glowing frame that shows the square a side landed on last (or, in
# gold, the square a token WOULD land on while the mouse is over its button).
# Returns an RGBA image, larger than the square by a margin of 0.3 * cell on
# every side (for the glow); the square is in the middle.
# Parameters:
#   cell   - size of one board square in pixels
#   player - player whose colour is used, or "preview" for gold
def render_marker(cell, player):
    accent = GOLD if player == "preview" else SIDE[player]["mid"]
    size = int(round(cell))
    margin = int(cell * 0.30)
    total = size + 2 * margin
    ss = 3
    thick = max(3.0, cell * 0.10)

    # Draws a rounded square outline, `inset` pixels inside the square. Returns
    # an "L" mask the size of the whole picture.
    # Parameters:
    #   inset - distance from the square's edge in pixels
    #   width - line width in pixels
    def ring_mask(inset, width):
        mask = Image.new("L", (total * ss, total * ss), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            ((margin + inset) * ss, (margin + inset) * ss,
             (margin + size - inset) * ss, (margin + size - inset) * ss),
            radius=cell * 0.14 * ss, outline=255, width=max(1, int(width * ss)))
        return mask.resize((total, total), Image.LANCZOS)

    outer = ring_mask(0.0, thick)
    inner = ring_mask(thick * 1.25, max(1.5, thick * 0.38))
    layer = glow_from_mask(outer, accent, cell * 0.09, 1.5)
    colour = Image.new("RGBA", (total, total), tuple(accent) + (255,))
    colour.putalpha(outer)
    layer.alpha_composite(colour)
    bright = Image.new("RGBA", (total, total), WHITE + (255,))
    bright.putalpha(inner)
    layer.alpha_composite(bright)
    return layer


# Paints one picture of the burst that marks a capture: an orange star with a
# pale centre and a glow that grows and then fades away. Returns an RGBA image,
# 3.4 squares wide and high, burst in the middle.
# Parameters:
#   cell - size of one board square in pixels
#   u    - time of the burst from 0.0 (start) to 1.0 (gone)
def render_boom(cell, u):
    grow = 1.0 - (1.0 - min(1.0, u * 1.6)) ** 2          # fast start
    fade = 1.0 - max(0.0, (u - 0.5) / 0.5)               # 1 -> 0 in 2nd half
    radius = cell * (0.25 + 0.95 * grow) * (0.35 + 0.65 * fade)
    size = int(cell * 3.4)
    ss = 2
    big = size * ss
    centre = big / 2.0
    turn = -90.0 + 50.0 * u
    outline = max(2.0, cell * 0.05) * ss

    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).polygon(
        star_points(centre, centre, radius * ss, radius * 0.52 * ss, 9, turn),
        fill=255)
    layer = glow_from_mask(mask, (255, 150, 20), radius * 0.45 * ss, 1.8)
    draw = ImageDraw.Draw(layer)
    draw.polygon(star_points(centre, centre, radius * ss, radius * 0.52 * ss,
                             9, turn),
                 fill=(255, 138, 31, 255), outline=(255, 243, 176, 255),
                 width=int(outline))
    draw.polygon(star_points(centre, centre, radius * 0.58 * ss,
                             radius * 0.30 * ss, 9, turn + 20.0),
                 fill=(255, 243, 176, 255))
    hot = radius * 0.16 * ss
    draw.ellipse((centre - hot, centre - hot, centre + hot, centre + hot),
                 fill=(255, 255, 255, 255))
    alpha = layer.getchannel("A").point(
        lambda value: int(value * (0.45 + 0.55 * fade)))
    layer.putalpha(alpha)
    return finish(layer, ss)


# Paints the small picture for the title bar and the task bar: a red 3-D die.
# Returns an RGBA image.
# Parameters:
#   size - width and height of the icon in pixels
def render_app_icon(size=64):
    die = Die((243, 240, 234), (206, 26, 36))
    return die.render(resting_rotation(5, twist=-8, tilt=(24, -28)), size,
                      view=1.62)


# ===== 13. THE SCENE (every picture, placed for one window size) =====

# Scene: everything that is painted for ONE window size. It builds the
# big still picture (background, logo, board, cards, labels) once, and
# hands out the moving parts (pawns, dice, buttons, texts) as small pictures
# on request. When the window changes size, the game makes a new Scene.
#
# Public attributes used by ludo_main_gui.py:
#   k, ox, oy         - pixels per du, and the offset of the 1280 x 794 design
#                       area inside the window
#   cell              - size of one board square in pixels
#   board_x, board_y  - pixel position of the board's top-left corner
#   still             - the still picture (an RGB image)
class Scene:

    # Paints the still picture for a window of this size.
    # Parameters:
    #   width             - window width in pixels
    #   height            - window height in pixels
    #   tokens_per_player - how many tokens each player has
    #   safe_squares      - ring squares that get a star
    #   student           - (name, student ID, module, project) for the student
    #                       card
    #   player_name       - name typed on the start page (shown on the score
    #                       card)
    def __init__(self, width, height, tokens_per_player, safe_squares, student,
                 player_name="You"):
        self.width, self.height = int(width), int(height)
        self.k = min(self.width / DESIGN_W, self.height / DESIGN_H)
        self.ox = (self.width - DESIGN_W * self.k) / 2
        self.oy = (self.height - DESIGN_H * self.k) / 2
        self.cell = CELL * self.k
        self.board_x = self.ox + BOARD_X * self.k
        self.board_y = self.oy + BOARD_Y * self.k
        self.tokens_per_player = tokens_per_player
        self.safe_squares = safe_squares
        self.student = student
        self.player_name = player_name
        self.cache = {}
        self.dice = {HUMAN: Die((243, 240, 234), (206, 26, 36),
                                light=FRONT_LIGHT),
                     AI: Die((243, 240, 234), (24, 100, 232),
                             light=FRONT_LIGHT)}
        self.die_px = int(round(3.5 * self.cell))
        self.still = self._paint_still()

    # Converts a length in du into pixels. Returns a float.
    # Parameters:
    #   du - a length in design units
    def px(self, du):
        return du * self.k

    # Converts a point in du into window pixels. Returns (x, y) in pixels.
    # Parameters:
    #   x - x in design units
    #   y - y in design units
    def pos(self, x, y):
        return self.ox + x * self.k, self.oy + y * self.k

    # Converts a rectangle in du (x1, y1, x2, y2) into window pixels. Returns
    # (x1, y1, x2, y2) in pixels (integers).
    # Parameters:
    #   rect - rectangle (x1, y1, x2, y2) in design units
    def box(self, rect):
        return du_box(rect, self.k, (self.ox, self.oy))

    # Converts a point of the board (in squares from the board's top-left
    # corner) into window pixels. Returns (x, y) in pixels.
    # Parameters:
    #   x - column on the board (may be fractional)
    #   y - row on the board (may be fractional)
    def grid_pos(self, x, y):
        return self.board_x + x * self.cell, self.board_y + y * self.cell

    # Paints the still picture: background, logo, board, captions, cards and
    # all their fixed labels and icons. Returns an RGB image of the window's
    # size.
    def _paint_still(self):
        k = self.k
        image = render_background(self.width, self.height).convert("RGBA")
        lx, ly = self.pos(LOGO_BOX[0], LOGO_BOX[1])
        put(image, render_logo(k), lx, ly)

        board, margin = render_board(self.cell, self.safe_squares,
                                     self.tokens_per_player)
        put(image, board, self.board_x - margin, self.board_y - margin)
        for player in (HUMAN, AI):
            cx, cy = CAPTION_CENTRE[player]
            width, height = (CAPTION_SIZE[player][0] * self.cell,
                             CAPTION_SIZE[player][1] * self.cell)
            caption = render_caption(width, height, player, k)
            x, y = self.grid_pos(cx, cy)
            put(image, caption, x - caption.width / 2, y - caption.height / 2)
        self._paint_cards(image)
        return image.convert("RGB")

    # Writes a fixed label on the still picture (position in du).
    # Parameters:
    #   image     - the PIL image to draw on
    #   x         - x in design units
    #   y         - y in design units
    #   text      - the text to show
    #   weight    - font weight name ("regular", "bold", ...)
    #   size      - font size in design units
    #   colour    - colour as an (r, g, b) tuple
    #   align     - horizontal alignment: "l" left, "c" centre, "r" right
    #   spacing   - extra space between letters in pixels
    #   max_width - widest the text may be, in pixels
    def _text(self, image, x, y, text, weight, size, colour, align="l",
              spacing=0.0, max_width=None):
        px, py = self.pos(x, y)
        font = (fit_font(weight, text, size * self.k, max_width * self.k)
                if max_width else get_font(weight, size * self.k))
        draw_text(image, px, py, text, font, colour, align=align, valign="c",
                  spacing=spacing * self.k)

    # Puts a picture centred on a point (position in du).
    # Parameters:
    #   image   - the PIL image to draw on
    #   picture - the icon picture
    #   x       - centre x in design units
    #   y       - centre y in design units
    def _icon(self, image, picture, x, y):
        px, py = self.pos(x, y)
        put(image, picture, px - picture.width / 2, py - picture.height / 2)

    # Draws a thin dividing line inside a card (coordinates in du).
    # Parameters:
    #   image - the PIL image to draw on
    #   x1    - start x in design units
    #   y1    - start y in design units
    #   x2    - end x in design units
    #   y2    - end y in design units
    def _line(self, image, x1, y1, x2, y2):
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        a, b = self.pos(x1, y1), self.pos(x2, y2)
        draw.line((a[0], a[1], b[0], b[1]), fill=(52, 96, 176, 150),
                  width=max(1, int(round(self.k * 1.1))))
        image.alpha_composite(layer)

    # Paints the five cards of the right-hand panel and every label and icon on
    # them that never changes.
    # Parameters:
    #   image - the still background picture
    def _paint_cards(self, image):
        k = self.k
        name, student_id, code, title = self.student
        for card, glow, sheen in (("student", (255, 70, 70), False),
                                  ("settings", None, False),
                                  ("status", None, True),
                                  ("score", None, False)):
            x1, y1, x2, y2 = self.box(CARDS[card])
            put(image, render_card(x2 - x1, y2 - y1, k, glow, sheen), x1, y1)
        x1, y1, x2, y2 = self.box((PANEL_X1, 599.0, PANEL_X2, 772.0))
        put(image, render_panel(x2 - x1, y2 - y1, k), x1, y1)

        # --- student card ---
        self._icon(image, icon_user(int(46 * k), (150, 188, 238)), 834, 54)
        self._text(image, 873, 44, name, "bold", 16.2, WHITE, max_width=205,
                   spacing=0.2)
        self._text(image, 873, 67, f"Student ID: {student_id}", "regular", 14.4,
                   TEXT, max_width=205)
        self._line(image, 1092, 34, 1092, 74)
        self._text(image, 1112, 44, code, "medium", 14.4, TEXT, max_width=140)
        self._text(image, 1112, 67, title, "regular", 13.0, MUTED, max_width=146)

        # --- settings card ---
        light = (176, 204, 246)
        self._icon(image, icon_gear(int(20 * k), light), 823, 123)
        self._text(image, 846, 123, "AI DIFFICULTY", "semibold", 12.6, TEXT,
                   spacing=0.35)
        self._line(image, 1056, 113, 1056, 180)
        self._icon(image, icon_people(int(23 * k), light), 1088, 123)
        self._text(image, 1109, 123, "WHO STARTS NEXT", "semibold", 12.6, TEXT,
                   spacing=0.35, max_width=150)
        self._line(image, 801, 187, 1257, 187)
        self._icon(image, icon_gauge(int(24 * k), light), 823, 206)
        self._text(image, 846, 206, "ANIMATION SPEED", "semibold", 12.6, TEXT,
                   spacing=0.35)
        self._line(image, 1032, 197, 1032, 252)

        # --- status card ---
        # (its little die is not painted here: it shows the number that was
        # just rolled, so the game puts it on the card - see status_die_picture)

        # --- score card ---
        name = self.player_name.strip()
        human_who = f"({name.upper()})" if name else ""
        for player, x, wx, tag, who in ((HUMAN, 847, 974, "PLAYER 1", human_who),
                                         (AI, 1093, 1218, "PLAYER 2", "(AI)")):
            self._icon(image, badge(int(27 * k), player), x - 23, 480)
            self._text(image, x, 472, tag, "bold", 14.5, SIDE[player]["text"])
            if who:
                self._text(image, x, 490, who, "bold", 12.5, SIDE[player]["text"],
                           max_width=84)
            self._text(image, wx, 483, "wins", "regular", 14.4, MUTED, align="r")
        self._line(image, 1029, 463, 1029, 528)

    # PICTURES THAT CHANGE WHILE THE GAME RUNS (every one is made once and
    # remembered)

    # Makes a picture the first time it is asked for and then keeps it. Returns
    # the picture.
    # Parameters:
    #   key  - name under which the picture is stored
    #   make - function that paints the picture if it is not stored yet
    def remember(self, key, make):
        picture = self.cache.get(key)
        if picture is None:
            picture = make()
            self.cache[key] = picture
        return picture

    # The picture of a row of choices with one chosen. Returns an RGBA image.
    # Parameters:
    #   name     - which setting row
    #   selected - the chosen option
    def segment_picture(self, name, selected):
        spec = SEGMENTS[name]
        x, y, w, h = spec["box"]
        index = spec["options"].index(selected)
        return self.remember(("seg", name, index), lambda: render_segments(
            spec["options"], index, w * self.k, h * self.k, self.k))

    # The area of a row of choices in pixels. Returns (x1, y1, x2, y2).
    # Parameters:
    #   name - which setting row
    def segment_region(self, name):
        x, y, w, h = SEGMENTS[name]["box"]
        return self.box((x, y, x + w, y + h))

    # The clickable area of a button in pixels. Returns (x1, y1, x2, y2).
    # Parameters:
    #   box - the button's layout box in design units
    def button_region(self, box):
        x, y, w, h = box
        return self.box((x, y, x + w, y + h))

    # The picture of NEW GAME or ROLL DICE in one of its states. It is larger
    # than the button (it includes the glow); `button_origin` says where to put
    # its top-left corner. Returns an RGBA image.
    # Parameters:
    #   name  - which button
    #   text  - the text to show
    #   state - "normal", "hover", "pressed" or "disabled"
    def button_picture(self, name, text, state):
        box = NEW_GAME_BOX if name == "new" else ROLL_BOX
        w, h = box[2] * self.k, box[3] * self.k
        kind = "green" if name == "new" else "gold"
        draw_state = "normal"
        if state == "off":
            kind = "off"
        elif state in ("hover", "press"):
            draw_state = state
        icon = icon_play if name == "new" else (
            lambda size, colour: icon_die(size, colour, (255, 200, 40)))
        return self.remember(("button", name, text, state), lambda: render_button(
            kind, w, h, self.k, text, draw_state, icon,
            WHITE if name == "new" and state != "off" else None))

    # Where the top-left corner of a button picture goes (the picture is larger
    # than the button, because of its glow). Returns (x, y) in pixels.
    # Parameters:
    #   box - the button's layout box in design units
    def button_origin(self, box):
        x, y = self.pos(box[0], box[1])
        pad = int(0.35 * int(box[3] * self.k))
        return x - pad, y - pad

    # The picture of a button that moves one of your pawns. Returns an RGBA
    # image.
    # Parameters:
    #   index - which token button (0 or 1)
    #   one   - first line of text
    #   two   - second line of text
    #   state - "normal", "hover", "pressed" or "disabled"
    def token_button_picture(self, index, one, two, state):
        box = TOKEN_BOXES[index]
        return self.remember(("tokbtn", index, one, two, state),
                             lambda: render_token_button(
                                 box[2] * self.k, box[3] * self.k, self.k, HUMAN,
                                 index + 1, one, two, state))

    # Where the top-left corner of a token button picture goes. Returns (x, y)
    # in pixels.
    # Parameters:
    #   index - which token button (0 or 1)
    def token_button_origin(self, index):
        box = TOKEN_BOXES[index]
        x, y = self.pos(box[0], box[1])
        pad = int(0.20 * int(box[3] * self.k))
        return x - pad, y - pad

    # The clickable area of a tab in pixels. Returns (x1, y1, x2, y2).
    # Parameters:
    #   index - tab number
    def tab_region(self, index):
        _, offset, width = TABS[index]
        x1 = PANEL_X1 + offset
        return self.box((x1, 555.0, x1 + width, 555.0 + TAB_HEIGHT))

    # The picture of one tab. Returns an RGBA image.
    # Parameters:
    #   index    - tab number
    #   selected - True if this item is the chosen one
    #   hover    - True while the mouse pointer is over it
    def tab_picture(self, index, selected, hover=False):
        label, _, width = TABS[index]
        icon = (lambda size, colour: icon_die(size, colour, GOLD)
                if index == 0 else icon_brain(size, colour) if index == 1
                else icon_book(size, colour))
        if index == 0:
            icon = (lambda size, colour: icon_die(
                size, colour, (255, 200, 40) if selected else (20, 40, 80)))
        return self.remember(("tab", index, selected, hover), lambda: render_tab(
            width * self.k, TAB_HEIGHT * self.k, self.k, label, icon, selected,
            hover))

    # The area (in pixels) where the log, thoughts or rules are shown. Returns
    # (x1, y1, x2, y2).
    def page_region(self):
        return self.box(PAGE_BOX)

    # A transparent picture with one line of text (for the status card, the
    # scoreboard and so on). Returns (picture, (x, y)): the image and where its
    # top-left goes.
    # Parameters:
    #   rect   - area (x1, y1, x2, y2) in design units
    #   text   - the text to show
    #   weight - font weight name ("regular", "bold", ...)
    #   size   - font size in design units
    #   colour - colour as an (r, g, b) tuple
    #   align  - horizontal alignment: "l" left, "c" centre, "r" right
    #   shadow - text shadow as (dx, dy, blur, colour), or None
    def text_slot(self, rect, text, weight, size, colour, align="l", shadow=None):
        x1, y1, x2, y2 = self.box(rect)
        scaled = None if shadow is None else (
            shadow[0] * self.k, shadow[1] * self.k, shadow[2] * self.k, shadow[3])
        picture = self.remember(
            ("text", rect, text, weight, size, colour, align, shadow),
            lambda: text_picture(x2 - x1, y2 - y1, text, weight, size * self.k,
                                 colour, align, scaled))
        return picture, (x1, y1)

    # The row of small circles under a player's score that fill up as tokens
    # reach the centre. Returns (picture, (x, y)).
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    #   filled - how many tokens reached the centre
    def home_circles(self, player, filled):
        spacing = 28.5
        x_left = 812.0 if player == HUMAN else 1060.0
        height = 26.0
        total = self.tokens_per_player

        # Paints the row of circles (the first `filled` ones are solid).
        # Returns an RGBA image.
        def make():
            w = int((spacing * total + 4) * self.k)
            h = int(height * self.k)
            ss = 4
            big = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
            draw = ImageDraw.Draw(big)
            side = SIDE[player]
            for index in range(total):
                cx = (12 + index * spacing) * self.k * ss
                cy = h * ss / 2
                r = 9.6 * self.k * ss
                box = (cx - r, cy - r, cx + r, cy + r)
                if index < filled:
                    draw.ellipse(box, fill=side["mid"] + (255,),
                                 outline=side["light"] + (255,),
                                 width=int(2.2 * self.k * ss))
                else:
                    draw.ellipse(box, outline=side["mid"] + (255,),
                                 width=int(2.2 * self.k * ss))
            return finish(big, ss)

        picture = self.remember(("circles", player, filled), make)
        x, y = self.pos(x_left, 513.0 - height / 2)
        return picture, (x, y)

    # The glowing frame of a die at a glow strength; it is larger than the
    # frame (it includes the glow), so `die_frame_origin` says where it goes.
    # Returns an RGBA image.
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    #   level  - glow strength step (0 = dim, 5 = brightest)
    def die_frame_picture(self, player, level):
        size = int(round(DIE_FRAME_SIZE * self.cell))
        return self.remember(("frame", player, level), lambda: render_die_frame(
            size, player, level / 5.0))

    # Where the top-left corner of a die frame picture goes. Returns (x, y) in
    # pixels.
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    def die_frame_origin(self, player):
        size = int(round(DIE_FRAME_SIZE * self.cell))
        cx, cy = self.grid_pos(*DIE_CENTRE[player])
        margin = int(size * 0.30)
        return cx - size / 2 - margin, cy - size / 2 - margin

    # The area of a die in pixels (clicking your die rolls it). Returns (x1,
    # y1, x2, y2).
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    def die_region(self, player):
        half = DIE_FRAME_SIZE / 2 * self.cell
        cx, cy = self.grid_pos(*DIE_CENTRE[player])
        return cx - half, cy - half, cx + half, cy + half

    # The soft patch under a die. Returns (picture, offset): the image and the
    # (dx, dy) in pixels from the frame's centre to the image's top-left
    # corner.
    def floor_shadow_picture(self):
        width = int(self.cell * 1.7)
        picture = self.remember(("floor",), lambda: render_floor_shadow(width))
        return picture, (-picture.width / 2, self.cell * 0.78 - picture.height / 2)

    # Paints a die in any position, for its frame. Returns an RGBA image of
    # die_px x die_px pixels.
    # Parameters:
    #   player   - the player number (HUMAN = red, AI = blue)
    #   rotation - 3 x 3 rotation matrix of the die
    #   quick    - True to paint small and enlarge (faster while tumbling)
    #   small    - size in pixels used when quick is True
    def die_picture(self, player, rotation, quick=False, small=112):
        size = self.die_px
        if quick and size > small:
            picture = self.dice[player].render(rotation, small)
            return picture.resize((size, size), Image.BILINEAR)
        return self.dice[player].render(rotation, size)

    # The little die on the status card, next to the message. After a roll it
    # shows exactly the number that was rolled (with the dots in the colour of
    # the player who rolled it); at any other time it is a plain cube seen from
    # a corner. Returns an RGBA image.
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    #   value  - the number shown on the die (1 to 6), or None
    def status_die_picture(self, player=HUMAN, value=None):
        size = int(58 * self.k)

        # Paints the picture the first time it is asked for. Returns an RGBA
        # image.
        def make():
            if value is None:
                plain = Die((246, 244, 240), (40, 52, 84))
                return plain.render(resting_rotation(5, twist=-8,
                                                     tilt=(24, -28)),
                                    size, view=1.62)
            twist = -5.0 if player == HUMAN else 5.0
            return self.dice[player].render(
                resting_rotation(value, twist=twist), size, view=1.62)

        key = ("statusdie", None, None) if value is None else (
            "statusdie", player, value)
        return self.remember(key, make)

    # Where the top-left corner of the status card's die picture goes (the die
    # is centred on the left of the card). Returns (x, y) in pixels.
    # Parameters:
    #   picture - the small die picture
    def status_die_origin(self, picture):
        px, py = self.pos(STATUS_DIE_CENTRE[0], STATUS_DIE_CENTRE[1])
        return px - picture.width / 2, py - picture.height / 2

    # The radius in pixels of a pawn at a size factor. Returns a float.
    # Parameters:
    #   scale - size factor of the pawn (1.0 = normal)
    def pawn_radius(self, scale):
        return PAWN_RADIUS * scale * self.cell

    # A pawn at a size factor (sizes are rounded to steps of 0.05 so the same
    # few pictures are used again and again). Returns an RGBA image.
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    #   index  - which token (0 or 1)
    #   scale  - size factor of the pawn (1.0 = normal)
    def pawn_picture(self, player, index, scale):
        bucket = int(round(scale * 20))
        return self.remember(("pawn", player, index, bucket), lambda: render_pawn(
            player, index + 1, self.pawn_radius(bucket / 20.0)))

    # The shadow of a pawn. Returns an RGBA image.
    # Parameters:
    #   scale - size factor of the pawn (1.0 = normal)
    #   lift  - how high the pawn is lifted (0 = on the board)
    def shadow_picture(self, scale, lift):
        bucket = int(round(scale * 20))
        amount = max(0.4, 1.0 - 0.30 * lift)
        step = int(round(amount * 10))
        return self.remember(("shadow", bucket, step), lambda: render_shadow(
            self.pawn_radius(bucket / 20.0), step / 10.0))

    # The golden ring round a pawn that can be moved. Returns an RGBA image.
    # Parameters:
    #   scale - size factor of the pawn (1.0 = normal)
    #   step  - pulse step of the ring (0 to 5)
    def halo_picture(self, scale, step):
        bucket = int(round(scale * 20))
        return self.remember(("halo", bucket, step), lambda: render_halo(
            self.pawn_radius(bucket / 20.0), step / 5.0))

    # The glowing frame round the square a side landed on last. Returns an RGBA
    # image (see marker_origin for where it goes).
    # Parameters:
    #   player - the player number (HUMAN = red, AI = blue)
    def marker_picture(self, player):
        return self.remember(("marker", player),
                             lambda: render_marker(self.cell, player))

    # Where the top-left corner of a landing frame picture goes. Returns (x, y)
    # in pixels.
    # Parameters:
    #   row    - grid row of the square
    #   column - grid column of the square
    def marker_origin(self, row, column):
        x, y = self.grid_pos(column, row)
        margin = int(self.cell * 0.30)
        return x - margin, y - margin

    # One picture of the capture burst (pictures are made once and kept).
    # Returns an RGBA image; its middle is the middle of the burst.
    # Parameters:
    #   u - time of the burst from 0.0 to 1.0
    def boom_picture(self, u):
        step = max(0, min(BOOM_STEPS, int(round(u * BOOM_STEPS))))
        return self.remember(("boom", step), lambda: render_boom(
            self.cell, step / float(BOOM_STEPS)))
