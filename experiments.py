# Name:       SELVARAJ SAKTHIVEL
# Student ID: 3607YZMI
# Module:     5FTC2067 Artificial Intelligence Principles - Mini Project
# File:       experiments.py
# Game:       Ludo Duel - experimental evaluation of the AI (for the report)
#
# Run:  python experiments.py        (400 games per match-up, about 10-15 min)
#       python experiments.py 100    (quick test with 100 games, about 3 min)
# Three experiments are printed as tables and saved to results.csv:
#   1. AI at search depth 1-4 against a RANDOM player
#   2. Deeper AI against shallower AI (head to head)
#   3. Different EVALUATION WEIGHTS (depth 2) against a random player
# Fairness: in every match-up the two players swap seats and who moves first,
# and the random seed is fixed so the results can be reproduced.

import csv
import math
import random
import sys
import time

from ludo_logic import new_game, roll_dice, apply_move, get_winner
from ai import choose_best_move, random_move, DEFAULT_WEIGHTS

DEFAULT_GAMES = 400     # games per match-up (override on the command line)
SEED = 2026             # fixed seed -> reproducible results


# Builds a player function that uses expectiminimax at a fixed depth. Returns a
# function f(state, dice) -> token index.
# Parameters:
#   depth   - how many moves ahead the search looks
#   weights - evaluation weights, or None for DEFAULT_WEIGHTS
#   timing  - list that collects the seconds per move, or None
def make_ai_player(depth, weights=None, timing=None):
    # Chooses a token for the AI; also measures how long the search took.
    # Returns the index of the token to move.
    # Parameters:
    #   state - the current GameState
    #   dice  - the number rolled (1 to 6)
    def player(state, dice):
        started = time.perf_counter()
        token_index, _ = choose_best_move(state, dice, depth, weights)
        if timing is not None:
            timing["seconds"] += time.perf_counter() - started
            timing["moves"] += 1
        return token_index
    return player


# Plays one complete game between two player functions. Returns the winning
# player (0 or 1).
# Parameters:
#   players      - two functions(state, dice) -> token index, one per side
#   first_player - the player who moves first
def play_game(players, first_player):
    state = new_game(first_player)
    while get_winner(state) is None:
        dice = roll_dice()
        token_index = players[state.current_player](state, dice)
        state = apply_move(state, token_index, dice)
    return get_winner(state)


# Plays many games of player A against player B, alternating seats and the
# starting player so the comparison is fair. Returns number of games won by
# player A.
# Parameters:
#   player_a - function(state, dice) -> token index for side A
#   player_b - function(state, dice) -> token index for side B
#   games    - number of games played
def run_match(player_a, player_b, games):
    a_wins = 0
    for game_number in range(games):
        a_seat = game_number % 2                # A sits at player 0 or 1
        first_player = (game_number // 2) % 2   # who moves first
        players = [None, None]
        players[a_seat] = player_a
        players[1 - a_seat] = player_b
        if play_game(players, first_player) == a_seat:
            a_wins += 1
    return a_wins


# 95% confidence margin of a win rate (normal approximation), so the report can
# say whether a difference is real or just dice luck. Returns the +/- margin as
# a fraction (0.05 = +/-5 percentage points).
# Parameters:
#   wins  - number of games won
#   games - number of games played
def confidence_margin(wins, games):
    rate = wins / games
    return 1.96 * math.sqrt(rate * (1 - rate) / games)


# Prints one result row and stores it for the CSV file.
# Parameters:
#   rows       - list that collects the rows for results.csv
#   experiment - name of the experiment
#   label      - name of the result row
#   wins       - number of games won
#   games      - number of games played
#   extra      - extra note printed after the row
def record_result(rows, experiment, label, wins, games, extra=""):
    rate = wins / games
    margin = confidence_margin(wins, games)
    print(f"  {label:<38} {wins:>4}/{games}  {rate:6.1%}  (+/-{margin:.1%})  {extra}")
    rows.append([experiment, label, wins, games, f"{rate:.3f}",
                 f"{margin:.3f}", extra])


# Runs the three experiments and writes results.csv.
# Parameters:
#   games - number of games per match-up
def main(games):
    rows = []

    # --- Experiment 1: depth vs random player ------------------------
    print(f"\nExperiment 1: AI depth vs Random player ({games} games each)")
    random.seed(SEED)
    for depth in (1, 2, 3, 4):
        timing = {"seconds": 0.0, "moves": 0}
        wins = run_match(make_ai_player(depth, timing=timing), random_move, games)
        ms = 1000 * timing["seconds"] / timing["moves"]
        record_result(rows, "1 depth vs random", f"AI depth {depth} vs Random",
                      wins, games, f"{ms:.1f} ms/move")

    # --- Experiment 2: deeper AI vs shallower AI ---------------------
    print(f"\nExperiment 2: deeper AI vs shallower AI ({games} games each)")
    random.seed(SEED)
    for deep, shallow in ((2, 1), (4, 1), (4, 2)):
        wins = run_match(make_ai_player(deep), make_ai_player(shallow), games)
        record_result(rows, "2 depth vs depth", f"AI depth {deep} vs AI depth {shallow}",
                      wins, games)

    # --- Experiment 3: evaluation weights (depth 2) vs random --------
    print(f"\nExperiment 3: evaluation weights, depth 2 vs Random ({games} games each)")
    random.seed(SEED)
    variants = {
        "Default weights": {},
        "Progress only": {"safe": 0, "threat": 0},
        "No threat term": {"threat": 0},
        "No safe-square bonus": {"safe": 0},
        "Heavy threat weight (x3)": {"threat": 3},
        "Extra finished bonus (10)": {"finished": 10},
    }
    for name, changes in variants.items():
        weights = dict(DEFAULT_WEIGHTS)
        weights.update(changes)
        wins = run_match(make_ai_player(2, weights), random_move, games)
        record_result(rows, "3 weights vs random", name, wins, games)

    # --- save everything ---------------------------------------------
    with open("results.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["experiment", "match-up", "wins", "games",
                         "win rate", "95% margin", "notes"])
        writer.writerows(rows)
    print("\nSaved to results.csv")


if __name__ == "__main__":
    number_of_games = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GAMES
    main(number_of_games)
