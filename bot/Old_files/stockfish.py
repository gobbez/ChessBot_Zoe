import chess
import chess.engine

from pathlib import Path

# Load df
THIS_FOLDER = Path(__file__).parent.resolve()
# Path to your Stockfish binary
STOCKFISH_PATH = THIS_FOLDER / "stockfish/stockfish-windows-x86-64-avx2.exe"


def stockfish_best_move(fen, opponent_elo):
    """
    Stockfish analyze position and finds best move with the thinking times based on opponent_elo
    :param fen: fen position
    :param opponent_elo: elo of opponent
    :return: best move for that thinking time
    """
    global STOCKFISH_PATH
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
        # Set the board position
        board = chess.Board(fen)

        def get_deep_time():
            # Get the best move
            if opponent_elo <= 700:
                deep_time = 0.7
            elif opponent_elo <= 1000:
                deep_time = 1.0
            elif opponent_elo <= 1500:
                deep_time = 2.0
            elif opponent_elo <= 2000:
                deep_time = 3.5
            elif opponent_elo <= 2500:
                deep_time = 5.0
            else:
                deep_time = 15.0
            return deep_time

        # Evaluate position CP to determine how bot is playing (the worse, the more thinking time)
        cp = evaluate_position_cp(fen)
        if cp > 0:
            deep_time = get_deep_time()
        elif -100 < cp < 0:
            deep_time = get_deep_time() * 2
        elif -200 < cp < -100:
            deep_time = get_deep_time() * 2.5
        elif cp < -200:
            deep_time = get_deep_time() * 4
        else:
            deep_time = get_deep_time()

        skill_level = 20
        engine.configure({"Skill Level": skill_level})
        result = engine.play(board, chess.engine.Limit(time=deep_time))
        return result.move

def evaluate_position_cp(fen):
    """
    Analyze the position and returns CP value (int)
    :param fen: fen position
    :return: CP value (int)
    """
    global STOCKFISH_PATH
    board = chess.Board(fen)
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
        info = engine.analyse(board, chess.engine.Limit(time=2.0))
        cp = str(info['score'].relative)
        cp = int(cp)
        return cp




def adapt_power(fen, opponent_elo):
    global STOCKFISH_PATH
    board = chess.Board(fen)
    list_legal_moves = list(board.legal_moves)

    # ELO to centipawn mapping
    diz_elo_cp = {
        1000: 150,
        1200: 100,
        1500: 65,
        1800: 50,
        2000: 45,
        2200: 40,
        2400: 30,
        2500: 20
    }

    adapted_move = None
    best_diff = float('inf')
    target_cp = None

    # Determine the target centipawn value based on the opponent's ELO
    for elo in sorted(diz_elo_cp.keys()):
        if abs(opponent_elo - elo) < best_diff:
            best_diff = abs(opponent_elo - elo)
            target_cp = diz_elo_cp[elo]

    if target_cp is None:
        return None

    best_move = None
    closest_cp_diff = float('inf')

    # Evaluate each legal move and find the one that best matches the target CP value
    for move in list_legal_moves:
        board.push(move)
        new_fen = board.fen()
        cp = evaluate_position_cp(new_fen)
        board.pop()
        if abs(cp - target_cp) < closest_cp_diff:
            closest_cp_diff = abs(cp - target_cp)
            best_move = move

    return best_move



fen = "rnbqk1n1/ppp2p2/3b2p1/3pp1N1/4P3/8/PPPP1PP1/RNB1KB1R b Qq - 1 7"
print(stockfish_best_move(fen, 2000))