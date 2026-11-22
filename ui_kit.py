# Name:       SELVARAJ SAKTHIVEL
# Student ID: 3607YZMI
# Module:     5FTC2067 Artificial Intelligence Principles - Mini Project
# File:       ui_kit.py
# Game:       Ludo Duel - drawing toolkit for the desktop window
#
# Small general drawing tools built on Pillow (and NumPy for the gradients).
# Nothing here knows about Ludo: it makes gradients, rounded shapes, glows,
# shadows and text, and lays one picture on top of another. ui_art.py uses
# them to paint every picture of the game window.
#
# CONVENTIONS: a picture is a Pillow "RGBA" image; a colour is (red, green,
# blue) or (red, green, blue, alpha), each 0-255; sizes are in pixels.
# "Supersampling" = draw 3-4 times larger and shrink, which makes edges smooth.

import math
import os

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# Fonts. The game uses the Poppins family (bundled in the fonts folder, see
# fonts/OFL-Poppins.txt for its licence). If a file is missing the next font in
# SYSTEM_FONTS that exists on this computer is used instead.
FONT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "fonts")
FONT_FILES = {
    "regular": "Poppins-Regular.ttf",
    "medium": "Poppins-Medium.ttf",
    "semibold": "Poppins-SemiBold.ttf",
    "bold": "Poppins-Bold.ttf",
    "extrabold": "Poppins-ExtraBold.ttf",
    "bolditalic": "Poppins-BoldItalic.ttf",
    "blackitalic": "Poppins-BlackItalic.ttf",
}
SYSTEM_FONTS = ("segoeui.ttf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
                "LiberationSans-Regular.ttf", "Helvetica.ttc")
_font_cache = {}

ARROW = "→"            # the arrow sign; Poppins has no glyph for it,
                            # so draw_text paints it as a shape instead


# ===== 1. COLOURS AND FONTS =====

# Mixes two colours (the alpha number too, if both have one). Returns the mixed
# colour as a tuple of integers.
# Parameters:
#   colour_a - first colour
#   colour_b - second colour
#   amount   - how much of colour_b to mix in (0.0 to 1.0)
def mix(colour_a, colour_b, amount):
    return tuple(int(round(a + (b - a) * amount))
                 for a, b in zip(colour_a, colour_b))


# Gives a Pillow font. Each font is only loaded once. Returns an ImageFont. If
# the bundled font file is missing, a system font (or Pillow's built-in one) is
# used.
# Parameters:
#   weight - font weight name ("regular", "bold", ...)
#   size   - font size in pixels
def get_font(weight, size):
    size = max(6, int(round(size)))
    key = (weight, size)
    font = _font_cache.get(key)
    if font is not None:
        return font
    path = os.path.join(FONT_FOLDER, FONT_FILES.get(weight, "Poppins-Bold.ttf"))
    candidates = [path] + list(SYSTEM_FONTS)
    for candidate in candidates:
        try:
            font = ImageFont.truetype(candidate, size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    _font_cache[key] = font
    return font


# ===== 2. GRADIENTS AND MASKS =====

# Makes a picture filled with a straight colour gradient. Returns an RGBA
# image.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
#   stops  - list of (position 0..1, colour) pairs of the gradient
#   angle  - direction of the gradient in degrees (90 = top to bottom)
def gradient_image(width, height, stops, angle=90.0):
    width, height = max(1, int(width)), max(1, int(height))
    radians = math.radians(angle)
    cos, sin = math.cos(radians), math.sin(radians)
    length = abs(width * cos) + abs(height * sin)
    xs = (np.arange(width, dtype=np.float32) + 0.5) - width / 2
    ys = (np.arange(height, dtype=np.float32) + 0.5) - height / 2
    t = (xs[None, :] * cos + ys[:, None] * sin) / max(length, 1e-6) + 0.5
    return _colour_ramp(t, stops)


# Makes a picture filled with a round colour gradient (a glow or a spot of
# light). Returns an RGBA image.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
#   centre - (x, y) of the centre as fractions 0..1
#   radius - radius in pixels
#   stops  - list of (position 0..1, colour) pairs of the gradient
#   squash - height / width ratio of the oval
def radial_gradient_image(width, height, centre, radius, stops, squash=1.0):
    width, height = max(1, int(width)), max(1, int(height))
    xs = (np.arange(width, dtype=np.float32) + 0.5) - centre[0]
    ys = ((np.arange(height, dtype=np.float32) + 0.5) - centre[1]) / squash
    t = np.sqrt(xs[None, :] ** 2 + ys[:, None] ** 2) / max(radius, 1e-6)
    return _colour_ramp(t, stops)


# Turns an array of positions into colours using the gradient stops. Returns an
# RGBA image with the same height and width as t.
# Parameters:
#   t     - NumPy array of positions 0..1
#   stops - list of (position 0..1, colour) pairs of the gradient
def _colour_ramp(t, stops):
    positions = [position for position, _ in stops]
    channels = []
    for index in range(4):
        values = [(colour[index] if len(colour) > index else 255)
                  for _, colour in stops]
        channels.append(np.interp(t, positions, values))
    data = np.stack(channels, axis=-1)
    return Image.fromarray(np.clip(data + 0.5, 0, 255).astype(np.uint8),
                           "RGBA")


# Makes a mask (a grey picture: white = inside, black = outside) in the shape
# of a rectangle with rounded corners, with smooth edges. Returns an "L" (grey)
# image.
# Parameters:
#   width   - width in pixels
#   height  - height in pixels
#   radius  - corner radius in pixels
#   corners - (top-left, top-right, bottom-right, bottom-left): True = rounded
#   ss      - supersampling factor (drawn this many times bigger, then shrunk)
def rounded_mask(width, height, radius, corners=(True, True, True, True),
                 ss=4):
    width, height = max(1, int(round(width))), max(1, int(round(height)))
    big = Image.new("L", (width * ss, height * ss), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, width * ss - 1, height * ss - 1), radius=radius * ss, fill=255,
        corners=corners)
    return big.resize((width, height), Image.LANCZOS)


# Makes a smooth mask from any drawing instructions. Returns an "L" (grey)
# image.
# Parameters:
#   width  - width in pixels
#   height - height in pixels
#   paint  - function(draw, ss) that draws the shape
#   ss     - supersampling factor (drawn this many times bigger, then shrunk)
def shape_mask(width, height, paint, ss=4):
    width, height = max(1, int(round(width))), max(1, int(round(height)))
    big = Image.new("L", (width * ss, height * ss), 0)
    paint(ImageDraw.Draw(big), ss)
    return big.resize((width, height), Image.LANCZOS)


# ===== 3. LAYERS (filling, glows, shadows, one picture on another) =====

# Cuts a picture to a shape: whatever the mask hides becomes see-through.
# Returns a new RGBA image.
# Parameters:
#   picture - a PIL RGBA image
#   mask    - greyscale "L" image giving the shape
#   opacity - overall opacity (0..1)
def through_mask(picture, mask, opacity=1.0):
    result = picture.copy()
    alpha = ImageChops.multiply(result.getchannel("A"), mask)
    if opacity < 1.0:
        alpha = alpha.point(lambda value: int(value * opacity))
    result.putalpha(alpha)
    return result


# Makes a soft glow in the shape of a mask: the mask is blurred and coloured.
# Returns an RGBA image the same size as the mask (leave a margin in the mask,
# otherwise the glow is cut off at the edge).
# Parameters:
#   mask     - greyscale "L" image giving the shape
#   colour   - colour of the glow
#   blur     - how soft the glow is, in pixels
#   strength - how strong the effect is (0..1)
def glow_from_mask(mask, colour, blur, strength=1.0):
    soft = mask.filter(ImageFilter.GaussianBlur(blur))
    if strength != 1.0:
        soft = soft.point(lambda value: int(min(255, value * strength)))
    layer = Image.new("RGBA", mask.size, (colour[0], colour[1], colour[2], 0))
    layer.putalpha(soft)
    return layer


# Lays a picture on top of another one (with see-through parts respected), at
# any position - even partly outside the base picture.
# Parameters:
#   base  - the RGBA picture that is drawn on
#   layer - the RGBA picture laid on top
#   x     - left of the layer in pixels
#   y     - top of the layer in pixels
def put(base, layer, x, y):
    x, y = int(round(x)), int(round(y))
    left, top = max(0, x), max(0, y)
    right = min(base.width, x + layer.width)
    bottom = min(base.height, y + layer.height)
    if right <= left or bottom <= top:
        return
    piece = layer.crop((left - x, top - y, right - x, bottom - y))
    base.alpha_composite(piece, (left, top))


# Lays a soft dark shadow of a shape on a picture.
# Parameters:
#   base   - the RGBA picture that is drawn on
#   mask   - greyscale "L" image giving the shape
#   x      - left of the shape in pixels
#   y      - top of the shape in pixels
#   blur   - blur radius in pixels
#   offset - (dx, dy) shift of the shadow
#   alpha  - darkness (0..255)
#   colour - colour of the shadow
def drop_shadow(base, mask, x, y, blur, offset=(0, 0), alpha=140,
                colour=(0, 0, 0)):
    pad = int(blur * 3)
    padded = Image.new("L", (mask.width + 2 * pad, mask.height + 2 * pad), 0)
    padded.paste(mask, (pad, pad))
    layer = glow_from_mask(padded, colour, blur, alpha / 255.0)
    put(base, layer, x - pad + offset[0], y - pad + offset[1])


# ===== 4. TEXT =====

# Width of the drawn arrow sign for a given font. Returns width in pixels.
# Parameters:
#   font - the PIL font used for the text
def _arrow_width(font):
    return font.size * 0.95


# Measures how wide a text is (the arrow sign counts as the drawn arrow).
# Returns the width in pixels.
# Parameters:
#   text    - the text to show
#   font    - the PIL font used for the text
#   spacing - extra space between letters in pixels
def text_width(text, font, spacing=0.0):
    width = 0.0
    for number, part in enumerate(text.split(ARROW)):
        if number:
            width += _arrow_width(font)
        if spacing:
            width += sum(font.getlength(letter) + spacing for letter in part)
        else:
            width += font.getlength(part)
    return width


# Height of the capital letters of a font (used to centre text neatly). Returns
# height in pixels.
# Parameters:
#   font - the PIL font used for the text
def cap_height(font):
    box = font.getbbox("H", anchor="ls")
    return -box[1]


# Draws the arrow sign "→" as a shape (thin line + arrow head).
# Parameters:
#   draw - the ImageDraw object to draw with
#   x    - left of the arrow in pixels
#   base - baseline in pixels
#   font - the PIL font used for the text
#   fill - fill colour
def _draw_arrow(draw, x, base, font, fill):
    size = font.size
    width = _arrow_width(font)
    middle = base - cap_height(font) * 0.5
    thick = max(1.0, size * 0.085)
    head = size * 0.26
    left, right = x + size * 0.1, x + width - size * 0.08
    draw.line((left, middle, right - head * 0.5, middle), fill=fill,
              width=int(round(thick)))
    draw.polygon([(right, middle), (right - head, middle - head * 0.62),
                  (right - head, middle + head * 0.62)], fill=fill)


# Writes text on a picture. It can align the text to the left, middle or right
# of a point, centre it vertically on the capital letters, add a shadow, and
# spread the letters out. Returns the width of the text in pixels.
# Parameters:
#   base        - the RGBA picture that is drawn on
#   x           - x of the anchor point in pixels
#   y           - y of the anchor point in pixels
#   text        - the text to show
#   font        - the PIL font used for the text
#   fill        - text colour
#   align       - horizontal alignment: "l" left, "c" centre, "r" right
#   valign      - vertical alignment: "t" top, "c" centre, "b" bottom
#   shadow      - text shadow as (dx, dy, blur, colour), or None
#   spacing     - extra space between letters in pixels
#   stroke      - outline width in pixels
#   stroke_fill - outline colour
def draw_text(base, x, y, text, font, fill, align="l", valign="c",
              shadow=None, spacing=0.0, stroke=0, stroke_fill=(0, 0, 0)):
    width = text_width(text, font, spacing)
    left = x - (width / 2 if align == "m" else width if align == "r" else 0)
    caps = cap_height(font)
    base_y = y + {"c": caps / 2, "b": 0, "t": caps}[valign]
    pad = int(font.size * 0.6) + (int(shadow[2] * 3) if shadow else 0)
    layer = Image.new("RGBA", (int(width + 2 * pad + 2),
                               int(font.size * 2 + 2 * pad)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    start_x, start_y = pad, pad + font.size * 1.3        # baseline in layer
    cursor = start_x
    for number, part in enumerate(text.split(ARROW)):
        if number:
            _draw_arrow(draw, cursor, start_y, font, fill)
            cursor += _arrow_width(font)
        if spacing:
            for letter in part:
                draw.text((cursor, start_y), letter, font=font, fill=fill,
                          anchor="ls", stroke_width=stroke,
                          stroke_fill=stroke_fill)
                cursor += font.getlength(letter) + spacing
        else:
            draw.text((cursor, start_y), part, font=font, fill=fill,
                      anchor="ls", stroke_width=stroke,
                      stroke_fill=stroke_fill)
            cursor += font.getlength(part)
    ox = left - start_x
    oy = base_y - start_y
    if shadow:
        dx, dy, blur, colour = shadow
        silhouette = layer.getchannel("A")
        glow = glow_from_mask(silhouette, colour[:3], blur,
                              (colour[3] if len(colour) > 3 else 255) / 255.0)
        put(base, glow, ox + dx, oy + dy)
    put(base, layer, ox, oy)
    return width


# Breaks a text into lines that fit a given width. Returns a list of strings
# (one per line).
# Parameters:
#   text      - the text to show
#   font      - the PIL font used for the text
#   max_width - widest the text may be, in pixels
def wrap_text(text, font, max_width):
    lines, line = [], ""
    for word in text.split(" "):
        trial = word if not line else line + " " + word
        if text_width(trial, font) <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


# ===== 5. SHAPES =====

# Corner points of a star (for the safe squares). Returns a list of (x, y)
# points.
# Parameters:
#   cx     - centre x
#   cy     - centre y
#   outer  - radius of the tips
#   inner  - radius of the inner corners
#   spikes - number of points of the star
#   turn   - rotation in degrees
def star_points(cx, cy, outer, inner, spikes=5, turn=-90.0):
    points = []
    for number in range(spikes * 2):
        radius = outer if number % 2 == 0 else inner
        angle = math.radians(turn + number * 180.0 / spikes)
        points.append((cx + radius * math.cos(angle),
                       cy + radius * math.sin(angle)))
    return points


# Shrinks a supersampled drawing to its final size (smooth edges). Returns the
# smaller RGBA image.
# Parameters:
#   picture - the big supersampled picture
#   ss      - supersampling factor (drawn this many times bigger, then shrunk)
def finish(picture, ss):
    if ss == 1:
        return picture
    return picture.resize((max(1, picture.width // ss),
                           max(1, picture.height // ss)), Image.LANCZOS)
