# Name:       SELVARAJ SAKTHIVEL
# Student ID: 3607YZMI
# Module:     5FTC2067 Artificial Intelligence Principles - Mini Project
# File:       ui_sound.py
# Game:       Ludo Duel - the sound effects of the desktop window

import os
import random
import shutil
import subprocess
import sys

try:
    import winsound
except ImportError:
    winsound = None

FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

# Sounds that have more than one version: one is picked at random each time.
VARIANTS = {"hop": ("hop", "hop2", "hop3")}


# Plays the game's sound effects; key M turns them on or off.
class SoundPlayer:

    # Sets up the player and finds a way to play .wav files on this computer.
    # Variables:
    #   enabled - True while the sound is on
    #   command - program used to play a .wav file when winsound is missing
    def __init__(self):
        self.enabled = True
        self.command = None
        if winsound is None:
            if sys.platform == "darwin" and shutil.which("afplay"):
                self.command = ["afplay"]
            elif shutil.which("paplay"):
                self.command = ["paplay"]
            elif shutil.which("aplay"):
                self.command = ["aplay", "-q"]

    # Plays a sound by name ("dice", "hop", "capture", ...) without waiting.
    # Parameters:
    #   name - sound name ("dice", "hop", "capture", "win", ...)
    def play(self, name):
        if not self.enabled:
            return
        name = random.choice(VARIANTS.get(name, (name,)))
        path = os.path.join(FOLDER, name + ".wav")
        if not os.path.exists(path):
            return
        try:
            if winsound is not None:
                winsound.PlaySound(path, winsound.SND_FILENAME
                                   | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            elif self.command:
                subprocess.Popen(self.command + [path],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        except Exception:
            pass

    # Turns the sound on or off. Returns True if it is now on.
    def toggle(self):
        self.enabled = not self.enabled
        if not self.enabled and winsound is not None:
            try:
                winsound.PlaySound(None, 0)
            except Exception:
                pass
        return self.enabled
