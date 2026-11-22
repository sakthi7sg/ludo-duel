# Name:       SELVARAJ SAKTHIVEL
# Student ID: 3607YZMI
# Module:     5FTC2067 Artificial Intelligence Principles - Mini Project
# File:       ai.py
# Game:       Ludo Duel - the computer player
#
# EXPECTIMINIMAX search = minimax extended with CHANCE nodes for the dice:
#   decision node, AI's turn        -> MAX: pick the token with the best value
#   decision node, opponent's turn  -> MIN: the opponent picks what is worst
#   chance node (before each move)  -> AVERAGE over the 6 die faces (1/6 each)
# Tree shape: [dice known] MAX -> chance -> MIN -> chance -> MAX -> ...
# At the search limit evaluate() scores the position (a heuristic for how
# close to victory the AI is).

import random

from ludo_logic import (apply_move, get_legal_moves, get_winner, ring_square,
                        FINISH, LAST_RING_PROGRESS, MAX_DICE, RING_SIZE,
                        SAFE_RING_SQUARES, START_RING_INDEX)

# Evaluation weights (experiments.py compares different settings):
#   progress - points per step of advancement (my total - opponent's total)
#   finished - extra bonus per token on FINISH (0: progress already rewards it)
#   safe     - bonus per token on a safe ring square (START or star square)
#   threat   - weight of the capture danger (see threatened_value)
#   win      - value of a won position (a lost one is -win)
DEFAULT_WEIGHTS = {
    "progress": 1.0,
    "finished": 0.0,
    "safe": 1.0,
    "threat": 1.0,
    "win": 1000.0,
}


# Adds up the progress that could be lost to a capture on the attacker's next
# roll. Returns the sum of progress of victim tokens that are "threatened". A
# victim token is threatened when it stands on a normal ring square (not a safe
# one) and an attacker token is 1 to 6 squares behind it on the ring, so one
# specific die roll would capture it. A token still in its yard counts as
# standing just behind its START square. Tokens on their home column or at
# FINISH can neither capture nor be captured.
# Parameters:
#   victim_player   - player whose tokens may be captured
#   victim_tokens   - progress of the victim's tokens
#   attacker_player - player who may capture
#   attacker_tokens - progress of the attacker's tokens
def threatened_value(victim_player, victim_tokens,
                     attacker_player, attacker_tokens):
    total = 0
    for victim_progress in victim_tokens:
        victim_square = ring_square(victim_player, victim_progress)
        if victim_square is None or victim_square in SAFE_RING_SQUARES:
            continue
        for attacker_progress in attacker_tokens:
            if attacker_progress > LAST_RING_PROGRESS:
                continue
            attacker_square = (START_RING_INDEX[attacker_player]
                               + attacker_progress - 1) % RING_SIZE
            gap = (victim_square - attacker_square) % RING_SIZE
            if (1 <= gap <= MAX_DICE
                    and attacker_progress + gap <= LAST_RING_PROGRESS):
                total += victim_progress
                break
    return total


# Counts how many of a player's tokens stand on a safe ring square. Returns an
# integer.
# Parameters:
#   player - the player number (HUMAN = red, AI = blue)
#   tokens - progress of each of the player's tokens
def count_on_safe_squares(player, tokens):
    return sum(1 for progress in tokens
               if ring_square(player, progress) in SAFE_RING_SQUARES)


# Heuristic score of a position from the AI's point of view. Higher = closer to
# victory for the AI. Returns a float. +win / -win for finished games,
# otherwise progress diff + finished diff + safe-square diff + threat term. The
# THREAT term is tempo-aware: only the player whose turn it is can strike next,
# and a specific roll has a 1/6 chance. So if it is the AI's turn we ADD
# (threatened opponent progress / 6), and if it is the opponent's turn we
# SUBTRACT (threatened AI progress / 6).
# Parameters:
#   state     - the current GameState (token positions and whose turn it is)
#   ai_player - the player number of the AI (whose score is maximised)
#   weights   - dictionary of evaluation weights (see DEFAULT_WEIGHTS)
def evaluate(state, ai_player, weights=DEFAULT_WEIGHTS):
    winner = get_winner(state)
    if winner is not None:
        return weights["win"] if winner == ai_player else -weights["win"]

    opponent = 1 - ai_player
    mine = state.tokens[ai_player]
    theirs = state.tokens[opponent]

    progress_diff = sum(mine) - sum(theirs)
    finished_diff = (sum(1 for p in mine if p == FINISH)
                     - sum(1 for p in theirs if p == FINISH))
    safe_diff = (count_on_safe_squares(ai_player, mine)
                 - count_on_safe_squares(opponent, theirs))

    if state.current_player == ai_player:
        threat = threatened_value(opponent, theirs,
                                  ai_player, mine) / MAX_DICE   # we may hit
    else:
        threat = -threatened_value(ai_player, mine,
                                   opponent, theirs) / MAX_DICE  # they may hit

    return (weights["progress"] * progress_diff
            + weights["finished"] * finished_diff
            + weights["safe"] * safe_diff
            + weights["threat"] * threat)


# Legal moves with duplicates removed. If both tokens stand on the same square,
# moving either gives the identical result, so only one is kept (this reduces
# the branching factor of the search). Returns a list of token indices.
# Parameters:
#   state - the current GameState (token positions and whose turn it is)
def get_unique_moves(state):
    seen_positions = set()
    unique = []
    for token_index in get_legal_moves(state):
        position = state.tokens[state.current_player][token_index]
        if position not in seen_positions:
            seen_positions.add(position)
            unique.append(token_index)
    return unique


# Expected value (for the AI) of a position. depth = how many more moves to
# look ahead (0 = stop). dice = None for a CHANCE node (average over the 6
# rolls); 1..6 for a DECISION node: MAX on the AI's turn, MIN otherwise.
# Parameters:
#   state     - the current GameState (token positions and whose turn it is)
#   depth     - how many moves ahead the search looks
#   ai_player - the player number of the AI (whose score is maximised)
#   weights   - dictionary of evaluation weights (see DEFAULT_WEIGHTS)
#   dice      - None at a CHANCE node, else the roll (1 to 6)
def expectiminimax(state, depth, ai_player, weights, dice=None):
    # Stop when somebody has won.
    if get_winner(state) is not None:
        return evaluate(state, ai_player, weights)

    # CHANCE node: average the value over every possible die roll.
    if dice is None:
        if depth == 0:
            return evaluate(state, ai_player, weights)
        total = 0.0
        for roll in range(1, MAX_DICE + 1):
            total += expectiminimax(state, depth, ai_player, weights, roll)
        return total / MAX_DICE

    # DECISION node: try every distinct token move for the roll.
    child_values = []
    for token_index in get_unique_moves(state):
        child_state = apply_move(state, token_index, dice)
        child_values.append(
            expectiminimax(child_state, depth - 1, ai_player, weights))

    if state.current_player == ai_player:
        return max(child_values)    # MAX node: AI picks its best token
    return min(child_values)        # MIN node: opponent picks AI's worst


# Picks the token the current player should move for a known dice roll.
# depth = moves to look ahead; mistake_chance = probability of ignoring the
# search and playing a random token (Easy mode). Returns (token_index, values)
# where values = {token_index: expectiminimax value}, shown in the "AI
# Thinking" tab. Ties are broken randomly.
# Parameters:
#   state          - the current GameState (token positions and whose turn it
#                    is)
#   dice           - the number rolled on the die (1 to 6)
#   depth          - how many moves ahead the search looks
#   weights        - dictionary of evaluation weights (see DEFAULT_WEIGHTS)
#   mistake_chance - chance (0..1) of playing a random token (Easy level)
def choose_best_move(state, dice, depth, weights=None, mistake_chance=0.0):
    if weights is None:
        weights = DEFAULT_WEIGHTS
    ai_player = state.current_player

    # Score each distinct move.
    value_at_position = {}
    for token_index in get_unique_moves(state):
        position = state.tokens[ai_player][token_index]
        child_state = apply_move(state, token_index, dice)
        value_at_position[position] = expectiminimax(
            child_state, depth - 1, ai_player, weights)

    # Report a value for every legal token (twin tokens share a value).
    values = {token_index: value_at_position[state.tokens[ai_player][token_index]]
              for token_index in get_legal_moves(state)}

    # Easy mode: sometimes ignore the search and play a random token.
    if random.random() < mistake_chance:
        return random.choice(list(values)), values

    best_value = max(values.values())
    best_tokens = [t for t, v in values.items() if v >= best_value - 1e-9]
    return random.choice(best_tokens), values


# Baseline opponent used in the experiments: picks any legal token (dice is
# unused, kept so every player has the same call signature). Returns a token
# index.
# Parameters:
#   state - the current GameState (token positions and whose turn it is)
#   dice  - the number rolled on the die (1 to 6)
def random_move(state, dice):
    return random.choice(get_legal_moves(state))
