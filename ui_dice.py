# Name:       SELVARAJ SAKTHIVEL
# Student ID: 3607YZMI
# Module:     5FTC2067 Artificial Intelligence Principles - Mini Project
# File:       ui_dice.py
# Game:       Ludo Duel - the 3-D die of the desktop window
#
# Paints a real-looking 3-D die: a cube with softly rounded edges, dents for
# the dots, a light from the upper left and a shiny highlight. The die can be
# turned to ANY position: every frame of the tumbling animation is painted
# fresh from a new rotation, and the last frame uses the rotation that shows
# the number that was rolled.
#
# RAY MARCHING: for every pixel a ray is shot from the camera and walked along
# by the distance to the nearest surface until it touches the die. The shape of
# the die is a distance formula (a "rounded box"), so rounded edges cost
# nothing extra. At the touching point we find the face, whether it lies inside
# a dot, the surface direction (the "normal") and from that the brightness. All
# pixels are calculated at once with NumPy.
# TERMS: "object space" = the die's own coordinates (the cube goes from -1 to
# +1 in x, y and z); "view space" = what the camera sees (x right, y up, z
# towards the camera). A rotation matrix R turns object space into view space.

import math

import numpy as np
from PIL import Image

HALF_VIEW = 1.75       # the picture shows x and y from -1.75 to +1.75
CORNER = 0.30          # how round the edges are (0 = sharp cube)
PIP_SPACING = 0.46     # distance of a dot from the middle of a face
PIP_RADIUS = 0.155     # size of a dot
MARCH_STEPS = 40       # most steps one ray may take (most need 3-4)
HIT_DISTANCE = 0.004   # a ray that gets this close has touched the die

# Direction towards the light, in view space (upper left, in front).
_light = np.array([-0.48, 0.66, 0.58])
LIGHT = _light / np.linalg.norm(_light)

# A more frontal light for the dice of the game board: the face that looks
# straight at the player (the number that was rolled) is then the brightest
# face of the die, so the eye goes to it first.
_front_light = np.array([-0.42, 0.55, 0.72])
FRONT_LIGHT = _front_light / np.linalg.norm(_front_light)

# How a die is turned when it lies still: (tip forward, turn sideways) in
# degrees. The angles are small on purpose: the rolled number is a big face
# that looks almost straight at the player, and the other two faces only
# show as narrow strips at the top and on the right.
REST_TILT = (13.0, -16.0)

# The number on each face of the die: (axis, sign) -> number. Opposite
# faces always add up to 7, as on a real die.
FACE_NUMBER = {(2, 1): 1, (2, -1): 6, (0, 1): 3, (0, -1): 4,
               (1, 1): 2, (1, -1): 5}
# The same thing the other way round: number -> direction the face looks.
FACE_NORMAL = {1: (0, 0, 1), 6: (0, 0, -1), 3: (1, 0, 0), 4: (-1, 0, 0),
               2: (0, 1, 0), 5: (0, -1, 0)}
# For a face on axis a: the two other axes that span the face.
FACE_PLANE = {0: (1, 2), 1: (0, 2), 2: (0, 1)}

# Where the dots sit on a face (x, y in face units), for each number.
_s = PIP_SPACING
PIP_LAYOUT = {
    1: [(0, 0)],
    2: [(-_s, _s), (_s, -_s)],
    3: [(-_s, _s), (0, 0), (_s, -_s)],
    4: [(-_s, _s), (_s, _s), (-_s, -_s), (_s, -_s)],
    5: [(-_s, _s), (_s, _s), (0, 0), (-_s, -_s), (_s, -_s)],
    6: [(-_s, _s), (_s, _s), (-_s, 0), (_s, 0), (-_s, -_s), (_s, -_s)],
}


# ===== 1. ROTATIONS =====

# Rotation matrix: turns things about the horizontal axis (tips the top of the
# die towards the camera when the angle is positive). Returns a 3 x 3 NumPy
# matrix.
# Parameters:
#   degrees - angle of rotation in degrees
def rot_x(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)


# Rotation matrix about the vertical axis (turns the die left or right).
# Returns a 3 x 3 NumPy matrix.
# Parameters:
#   degrees - angle of rotation in degrees
def rot_y(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)


# Rotation matrix about the axis pointing at the camera (spins the die like a
# coin lying flat on the screen). Returns a 3 x 3 NumPy matrix.
# Parameters:
#   degrees - angle of rotation in degrees
def rot_z(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)


# Rotation matrix about any axis (Rodrigues' formula). Returns a 3 x 3 NumPy
# matrix.
# Parameters:
#   axis    - axis to turn round (3 numbers)
#   degrees - angle of rotation in degrees
def rot_axis(axis, degrees):
    x, y, z = np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis)
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    t = 1.0 - c
    return np.array([[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
                     [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
                     [t * x * z - s * y, t * y * z + s * x, t * z * z + c]])


# The rotation that turns the die so that the face with a given number looks
# straight at the camera. Returns a 3 x 3 NumPy matrix.
# Parameters:
#   value - the face that must point at the camera (1 to 6)
def face_rotation(value):
    start = np.array(FACE_NORMAL[value], dtype=np.float64)
    goal = np.array([0.0, 0.0, 1.0])
    if np.allclose(start, -goal):
        return rot_x(180)
    axis = np.cross(start, goal)
    if not axis.any():
        return np.eye(3)
    angle = math.degrees(math.acos(max(-1.0, min(1.0, float(start @ goal)))))
    return rot_axis(axis, angle)


# Works out the "halfway" direction between a light and the camera, which
# decides where the shiny highlight of the die appears. Returns a unit vector
# (NumPy array of 3 numbers).
# Parameters:
#   light - direction towards the light (unit vector)
def half_vector_of(light):
    half = np.asarray(light, dtype=np.float64) + np.array([0.0, 0.0, 1.0])
    return half / np.linalg.norm(half)


# The position a die lies in when it has stopped: the rolled number is the big
# face in front, only slightly turned (see REST_TILT), so that its dots can be
# read at a glance. The top and the right side show as narrow strips so that
# the die still looks like a cube, but they cannot be mistaken for the number
# that was rolled. Returns a 3 x 3 NumPy matrix (object space -> view space).
# Parameters:
#   value - the number rolled (1 to 6)
#   twist - turn of the die on the table in degrees
#   tilt  - (x, y) tilt in degrees so three faces show
def resting_rotation(value, twist=0.0, tilt=REST_TILT):
    return rot_z(twist) @ rot_x(tilt[0]) @ rot_y(tilt[1]) @ face_rotation(value)


# ===== 2. THE DIE =====

# Die: a die of one colour scheme that can be painted in any position.
class Die:

    # Creates a die. body and pip are the colours of the cube and of the dots;
    # shine is the strength of the white highlight (0 = matt, 1 = glossy);
    # light is a unit vector towards the light in view space (None = LIGHT).
    # Parameters:
    #   body  - colour of the die
    #   pip   - colour of the dots
    #   shine - strength of the shiny highlight (0..1)
    #   light - direction towards the light, or None for LIGHT
    def __init__(self, body, pip, shine=0.34, light=None):
        self.body = np.array(body[:3], dtype=np.float64)
        self.pip = np.array(pip[:3], dtype=np.float64)
        self.shine = shine
        self.light = LIGHT if light is None else np.asarray(light, dtype=np.float64)
        self.half_vector = half_vector_of(self.light)
        self._grids = {}

    # Paints the die in a given position. Returns an RGBA image of size x size
    # pixels (the die only; the area around it is see-through).
    # Parameters:
    #   rotation - 3 x 3 rotation matrix of the die
    #   size     - width and height of the picture in pixels
    #   view     - half the width of the visible area in die units
    def render(self, rotation, size, view=HALF_VIEW):
        rot = np.asarray(rotation, dtype=np.float64)
        n = int(size)
        pixel = 2.0 * view / n
        grid = self._grids.get((n, view))
        if grid is None:
            coords = (np.arange(n, dtype=np.float64) + 0.5) * pixel - view
            xs, ys = np.meshgrid(coords, -coords)
            grid = (xs.ravel(), ys.ravel())
            self._grids[(n, view)] = grid
        x, y = grid

        hit, colour = self._trace(x, y, rot)
        mask = hit.reshape(n, n)
        padded = np.pad(mask, 1, constant_values=False)
        up, down = padded[:-2, 1:-1], padded[2:, 1:-1]
        left, right = padded[1:-1, :-2], padded[1:-1, 2:]
        edge = ((mask & ~(up & down & left & right))
                | (~mask & (up | down | left | right))).ravel()

        alpha = hit.astype(np.float64)
        edge_index = np.nonzero(edge)[0]
        if edge_index.size:                       # smooth the outline
            seen = np.zeros(edge_index.size)
            summed = np.zeros((edge_index.size, 3))
            for dx, dy in ((-0.25, -0.25), (0.25, -0.25),
                           (-0.25, 0.25), (0.25, 0.25)):
                got, shade = self._trace(x[edge_index] + dx * pixel,
                                         y[edge_index] + dy * pixel, rot)
                seen += got
                summed += shade * got[:, None]
            colour[edge_index] = summed / np.maximum(seen, 1.0)[:, None]
            alpha[edge_index] = seen / 4.0

        data = np.zeros((n * n, 4), dtype=np.uint8)
        data[:, :3] = np.clip(colour + 0.5, 0, 255).astype(np.uint8)
        data[:, 3] = np.clip(alpha * 255 + 0.5, 0, 255).astype(np.uint8)
        return Image.fromarray(data.reshape(n, n, 4), "RGBA")

    # Shoots one ray for every given point of the picture and works out whether
    # it touches the die and what colour that spot has. Returns (touched,
    # colour): a True/False array and an array of (r, g, b) numbers 0..255, one
    # row per ray.
    # Parameters:
    #   x   - array of ray x positions (view space)
    #   y   - array of ray y positions (view space)
    #   rot - 3 x 3 rotation matrix of the die
    def _trace(self, x, y, rot):
        count = x.shape[0]
        direction = -rot[2]                    # the rays' direction, object space
        origin = (x[:, None] * rot[0] + y[:, None] * rot[1]
                  + 6.0 * rot[2])              # ray start, object space
        safe = np.where(np.abs(direction) < 1e-9, 1e-9, direction)
        t1 = (-1.0 - origin) / safe
        t2 = (1.0 - origin) / safe
        enter = np.minimum(t1, t2).max(axis=1)
        leave = np.maximum(t1, t2).min(axis=1)
        candidates = np.nonzero(leave > np.maximum(enter, 0.0))[0]

        touched = np.zeros(count, dtype=bool)
        colour = np.zeros((count, 3), dtype=np.float64)
        if candidates.size == 0:
            return touched, colour

        start = origin[candidates]
        walked = enter[candidates].copy()
        stop_at = leave[candidates] + 0.25     # a ray past this has missed
        inner = 1.0 - CORNER
        landed = np.zeros(candidates.size, dtype=bool)
        active = np.arange(candidates.size)
        for _ in range(MARCH_STEPS):           # walk along the rays
            point = start[active] + direction * walked[active][:, None]
            q = np.abs(point) - inner
            gap = (np.sqrt((np.maximum(q, 0.0) ** 2).sum(axis=1))
                   + np.minimum(q.max(axis=1), 0.0) - CORNER)
            arrived = gap < HIT_DISTANCE
            landed[active[arrived]] = True
            walked[active] += gap
            active = active[~arrived & (walked[active] < stop_at[active])]
            if active.size == 0:
                break
        on = landed
        if not on.any():
            return touched, colour
        point = start + direction * walked[:, None]

        where = candidates[on]
        touched[where] = True
        colour[where] = self._shade(point[on], rot)
        return touched, colour

    # Works out the colour of the die at some points on its surface. Returns
    # array (m, 3) of (r, g, b) numbers, 0..255 (may exceed 255).
    # Parameters:
    #   point - array of hit points on the die surface
    #   rot   - 3 x 3 rotation matrix of the die
    def _shade(self, point, rot):
        m = point.shape[0]
        inner = 1.0 - CORNER
        sign = np.sign(point)
        sign[sign == 0] = 1.0
        q = np.maximum(np.abs(point) - inner, 0.0)
        normal = sign * q
        normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True),
                             1e-9)

        # Which face is it, and how far is the point from the nearest dot?
        axis = np.argmax(np.abs(point), axis=1)
        face_sign = sign[np.arange(m), axis]
        nearest = np.full(m, 9.0)
        offset_u = np.zeros(m)
        offset_v = np.zeros(m)
        for (face_axis, direction), number in FACE_NUMBER.items():
            chosen = np.nonzero((axis == face_axis)
                                & (face_sign == direction))[0]
            if chosen.size == 0:
                continue
            a1, a2 = FACE_PLANE[face_axis]
            u, v = point[chosen, a1], point[chosen, a2]
            for pip_u, pip_v in PIP_LAYOUT[number]:
                du, dv = u - pip_u, v - pip_v
                distance = np.sqrt(du * du + dv * dv)
                closer = distance < nearest[chosen]
                if closer.any():
                    take = chosen[closer]
                    nearest[take] = distance[closer]
                    offset_u[take] = du[closer]
                    offset_v[take] = dv[closer]
                    # remember the plane axes of this face for the dent
        t = nearest / PIP_RADIUS
        inside = np.clip((1.0 + 0.10 - t) / 0.20, 0.0, 1.0)        # dot or not
        bowl = np.clip((1.12 - t) / 0.85, 0.0, 1.0)                # the dent

        # A dot is a small dent: its walls tilt the surface towards the
        # middle of the dot, which makes one side dark and the other light.
        tilt = 1.15 * bowl
        for face_axis in (0, 1, 2):
            chosen = np.nonzero(axis == face_axis)[0]
            if chosen.size == 0:
                continue
            a1, a2 = FACE_PLANE[face_axis]
            normal[chosen, a1] -= tilt[chosen] * offset_u[chosen] / PIP_RADIUS
            normal[chosen, a2] -= tilt[chosen] * offset_v[chosen] / PIP_RADIUS
        normal /= np.linalg.norm(normal, axis=1, keepdims=True)

        view_normal = normal @ rot.T
        lambert = np.clip(view_normal @ self.light, 0.0, 1.0)
        sky = 0.5 + 0.5 * view_normal[:, 1]
        ambient = 0.50 + 0.22 * sky
        spec = np.clip(view_normal @ self.half_vector, 0.0, 1.0) ** 26
        rim = (1.0 - np.clip(view_normal[:, 2], 0.0, 1.0)) ** 2.6

        base = (self.body[None, :] * (1.0 - inside[:, None])
                + self.pip[None, :] * inside[:, None])
        cool = np.array([0.80, 0.87, 1.00])
        warm = np.array([1.00, 0.985, 0.95])
        light = (ambient[:, None] * cool[None, :]
                 + 0.58 * lambert[:, None] * warm[None, :])
        colour = base * light
        colour += (255.0 * self.shine) * spec[:, None] * (1.0 - 0.55 * inside)[:, None]
        colour += rim[:, None] * np.array([18.0, 26.0, 40.0])[None, :]
        return colour
