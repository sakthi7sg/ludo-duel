# Name:       SELVARAJ SAKTHIVEL
# Student ID: 3607YZMI
# Module:     5FTC2067 Artificial Intelligence Principles - Mini Project
# File:       ludo_logic.py
# Game:       Ludo Duel - the rules only (no AI, no user interface)
#
# Test it on its own:  python ludo_logic.py
#
# BOARD     A ring of 52 squares shared by both players. You (player 0, red)
#           start in the top-right corner and the computer (player 1, blue) in
#           the bottom-left, so player 1's START is 26 squares round the ring.
# PROGRESS  How far a token has travelled: 0 = waiting in its yard, 1..51 = on
#           the ring (1 = its own START square), 52..56 = its private HOME
#           COLUMN (nobody can capture it there), 57 = FINISH, the centre.
# RULES     * Each player has 2 tokens. Roll a die (1-6) and move ONE token
#             that many steps. No 6 is needed to leave the yard: a roll of r
#             lands on step r (a roll of 1 lands on START).
#           * Landing on a ring square that holds an opponent token captures
#             it (it goes back to its yard). The 2 START squares and the 6
#             star squares are SAFE.
#           * No exact roll is needed to finish (overshooting stops at FINISH)
#             and a 6 gives no extra turn (this keeps the AI's search small).
#           * The first player with both tokens on FINISH wins.
# STATE     GameState(tokens, current_player), tokens = ((a0, a1), (b0, b1)):
#           the progress of player 0's and player 1's tokens. It is immutable
#           (tuples), so the AI can copy it cheaply.

import random
from collections import namedtuple

# ----- Game constants -----
START = 0                    # progress of a token waiting in its yard
LAST_RING_PROGRESS = 51      # last step on the shared ring (tip of own arm)
HOME_COLUMN_FIRST = 52       # first square of the private home column
FINISH = 57                  # the centre; a token here can no longer move
RING_SIZE = 52               # number of squares on the shared ring
START_RING_INDEX = (0, 26)   # ring square of each player's START square
SAFE_RING_SQUARES = (0, 8, 13, 21, 26, 34, 39, 47)   # 2 starts + 6 stars
TOKENS_PER_PLAYER = 2        # number of tokens each player owns
MAX_DICE = 6                 # the die has faces 1..MAX_DICE

# One complete game position.
GameState = namedtuple("GameState", ["tokens", "current_player"])


# Creates the starting position of a new game. Returns a GameState with every
# token in its yard.
# Parameters:
#   first_player - the player who moves first
def new_game(first_player=0):
    starting_tokens = ((START,) * TOKENS_PER_PLAYER,
                       (START,) * TOKENS_PER_PLAYER)
    return GameState(starting_tokens, first_player)


# Simulates rolling one fair six-sided die (this is the "chance" element).
# Returns an integer from 1 to 6.
def roll_dice():
    return random.randint(1, MAX_DICE)


# Works out where a token would land after moving. Returns the new progress,
# never more than FINISH (overshoot is allowed and simply stops at FINISH).
# Parameters:
#   position - progress of the token before the move
#   dice     - the number rolled on the die (1 to 6)
def destination(position, dice):
    return min(position + dice, FINISH)


# Converts a token's progress into the square of the shared ring it stands on
# (0..51, numbered clockwise from player 0's START square). Returns the ring
# square, or None if the token is not on the ring (in its yard, on its home
# column, or at FINISH).
# Parameters:
#   player   - the player number (HUMAN = red, AI = blue)
#   progress - steps the token has moved (1 to 51 on the ring)
def ring_square(player, progress):
    if 1 <= progress <= LAST_RING_PROGRESS:
        return (START_RING_INDEX[player] + progress - 1) % RING_SIZE
    return None


# Lists which of the current player's tokens can be moved. Returns a list of
# token indices (0 or 1). A token on FINISH cannot move. While the game is not
# over there is always at least one legal move, so "no move available" never
# happens.
# Parameters:
#   state - the current GameState (token positions and whose turn it is)
def get_legal_moves(state):
    my_tokens = state.tokens[state.current_player]
    return [index for index, position in enumerate(my_tokens)
            if position < FINISH]


# Finds the opponent tokens a move would send back to their yard (without
# making the move). Returns a list of opponent token indices (empty if nothing
# is captured: the landing square is safe, off the ring, or empty).
# Parameters:
#   state       - the current GameState (token positions and whose turn it is)
#   token_index - which token of the player moves (0 or 1)
#   dice        - the number rolled on the die (1 to 6)
def captured_tokens(state, token_index, dice):
    player = state.current_player
    opponent = 1 - player
    landing = destination(state.tokens[player][token_index], dice)
    square = ring_square(player, landing)
    if square is None or square in SAFE_RING_SQUARES:
        return []
    return [index for index, position in enumerate(state.tokens[opponent])
            if ring_square(opponent, position) == square]


# Checks whether a move would capture an opponent token. Returns True if at
# least one opponent token would be captured.
# Parameters:
#   state       - the current GameState (token positions and whose turn it is)
#   token_index - which token of the player moves (0 or 1)
#   dice        - the number rolled on the die (1 to 6)
def is_capture(state, token_index, dice):
    return len(captured_tokens(state, token_index, dice)) > 0


# Plays one move and returns the NEW state (the old state is unchanged).
# Captured opponent tokens go back to their yard and the turn passes to the
# other player. Returns the GameState after the move.
# Parameters:
#   state       - the current GameState (token positions and whose turn it is)
#   token_index - which token of the player moves (0 or 1)
#   dice        - the number rolled on the die (1 to 6)
def apply_move(state, token_index, dice):
    player = state.current_player
    opponent = 1 - player

    # Move the chosen token.
    my_tokens = list(state.tokens[player])
    my_tokens[token_index] = destination(my_tokens[token_index], dice)

    # Send every captured opponent token (even a stacked pair) home.
    opponent_tokens = list(state.tokens[opponent])
    for index in captured_tokens(state, token_index, dice):
        opponent_tokens[index] = START

    # Rebuild the (player 0, player 1) token tuple in the right order.
    new_tokens = [None, None]
    new_tokens[player] = tuple(my_tokens)
    new_tokens[opponent] = tuple(opponent_tokens)
    return GameState(tuple(new_tokens), opponent)


# Checks whether somebody has won. Returns 0 or 1 for the winning player, or
# None if the game continues.
# Parameters:
#   state - the current GameState (token positions and whose turn it is)
def get_winner(state):
    for player in (0, 1):
        if all(position == FINISH for position in state.tokens[player]):
            return player
    return None


# Self-test (python ludo_logic.py): plays many random-vs-random games to prove
# the rules always reach a winner, checks the rules on every move, and prints
# the start of one sample game.
if __name__ == "__main__":
    random.seed(1)

    # --- one sample game, first 12 turns printed ----------------------
    game = new_game()
    turn = 0
    print("Sample game (random vs random), first 12 turns:")
    while get_winner(game) is None:
        turn += 1
        roll = roll_dice()
        chosen = random.choice(get_legal_moves(game))
        mover = game.current_player
        hit = is_capture(game, chosen, roll)
        game = apply_move(game, chosen, roll)
        if turn <= 12:
            print(f"Turn {turn:2d}: P{mover} rolled {roll}, moved token "
                  f"{chosen + 1}{' (CAPTURE!)' if hit else ''} -> "
                  f"{game.tokens}")
    print(f"... Winner: Player {get_winner(game)} after {turn} turns\n")

    # --- 1000 games: every game must finish, every move must be legal --
    wins = [0, 0]
    total_turns = 0
    total_captures = 0
    for _ in range(1000):
        game = new_game()
        while get_winner(game) is None:
            roll = roll_dice()
            chosen = random.choice(get_legal_moves(game))
            if is_capture(game, chosen, roll):
                total_captures += 1
            game = apply_move(game, chosen, roll)
            total_turns += 1
            assert all(0 <= p <= FINISH for side in game.tokens for p in side)
        wins[get_winner(game)] += 1
    print(f"1000 random games finished. Wins: P0={wins[0]}, P1={wins[1]}, "
          f"average length = {total_turns / 1000:.1f} turns, "
          f"captures per game = {total_captures / 1000:.1f}")
