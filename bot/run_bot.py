import berserk
import yaml
import chess
import chess.engine
import random
import pandas as pd
import threading
import time
from pathlib import Path

# Load Stockfish
THIS_FOLDER = Path(__file__).parent.resolve()
# Path to your Stockfish binary
STOCKFISH_PATH = THIS_FOLDER / "stockfish/stockfish-windows-x86-64-avx2.exe"
config_path = THIS_FOLDER / "config.yml"

# List of active games id:
list_playing_id = []


# Load configuration from file config.yml
with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

# Configure Lichess client with token
session = berserk.TokenSession(config['token'])
client = berserk.Client(session=session)


# STOCKFISH FUNCTIONS
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
        if "#" in cp:
            cp = cp[1:]
            cp = int(cp) * 1000
        else:
            cp = int(cp)
        return cp


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
                deep_time = 0.2
            elif opponent_elo <= 1000:
                deep_time = 0.5
            elif opponent_elo <= 1500:
                deep_time = 1.0
            elif opponent_elo <= 2000:
                deep_time = 1.5
            elif opponent_elo <= 2300:
                deep_time = 2.3
            elif opponent_elo <= 2500:
                deep_time = 5.0
            else:
                deep_time = 10.0
            return deep_time

        # Evaluate position CP to determine how bot is playing (the worse, the more thinking time)
        cp = evaluate_position_cp(fen)
        if cp > 0:
            deep_time = get_deep_time()
        elif -50 < cp <= 0:
            deep_time = get_deep_time() * 1.1
        elif -100 < cp <= 50:
            deep_time = get_deep_time() * 1.4
        elif -200 < cp <= -100:
            deep_time = get_deep_time() * 2
        elif -400 < cp <= -200:
            deep_time = get_deep_time() * 4
        elif cp < -400:
            deep_time = get_deep_time() * 7
        else:
            deep_time = get_deep_time()
        result = engine.play(board, chess.engine.Limit(time=deep_time))
        return result.move


def handle_game_bot_turn(game_id, fen, elo_opponent):
    """
    This function handles the moves on Lichess and saves moves.
    :param game_id: the game id that the bot is currently playing
    :param fen: the fen position, to pass to read_fen_database to extract move
    :param elo_opponent: opponent Lichess elo
    """
    chess_board = chess.Board()
    move_number = 1  # Initialize move number

    for event in client.bots.stream_game_state(game_id):
        print(f"Playing: {event['id']}")
        if 'state' not in event:
            continue  # Skip this event if it doesn't contain the 'state' key

        # Update the chess board with all moves
        moves = event['state']['moves'].split()
        list_white = []
        list_black = []
        for i, move in enumerate(moves):
            if i % 2 == 0:
                list_white.append(move)
            else:
                list_black.append(move)
                move_number += 1
            try:
                chess_board.push_uci(move)
            except ValueError:
                # Handle the case where the move is not valid (e.g., game start)
                continue
        # In case white has a move more, meaning it's black turn, update it with an x
        if len(list_white) != len(list_black):
            list_black.append('x')
        # Save moves in a DataFrame (not used anymore)
        # df_moves = pd.DataFrame({'white': list_white, 'black': list_black})

        if 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR' in fen:
            # First move
            if chess_board.turn == chess.WHITE:
                initial_move = 'g2g3'
            else:
                initial_move = 'g7g6'
            client.bots.make_move(game_id, initial_move)
            chess_board.push_uci(initial_move)
            print('I made first move')
        else:
            # Use Stockfish 17 to find best move
            next_move = stockfish_best_move(fen, elo_opponent)
            if next_move:
                try:
                    client.bots.make_move(game_id, next_move.uci())
                    chess_board.push(next_move)
                    print('I moved')
                except Exception as e:
                    print(f"Invalid move: {e}")
                    list_legal_moves = list(chess_board.legal_moves)
                    rand_move = list_legal_moves[random.randint(0, len(list_legal_moves) - 1)]
                    client.bots.make_move(game_id, rand_move.uci())
                    chess_board.push(rand_move)
                    print('Invalid move.. i moved random')

            else:
                print('Move not found, i go random..')
                list_legal_moves = list(chess_board.legal_moves)
                rand_move = list_legal_moves[random.randint(0, len(list_legal_moves) - 1)]
                client.bots.make_move(game_id, rand_move.uci())
                chess_board.push(rand_move)
        list_playing_id.remove(game_id)
        return

def main():
    game_threads = []

    def handle_events():
        try:
            events = client.bots.stream_incoming_events()
            for event in events:
                print(event['type'])
                if event['type'] == 'challenge':
                    if not event['challenge']['rated']:
                        print('Challenge accepted!')
                        # Accepting only unrated games for now
                        challenge_id = event['challenge']['id']
                        client.bots.accept_challenge(challenge_id)

                elif event['type'] == 'gameStart':
                    board_event = event['game']
                    game_id = event['game']['id']
                    # Check if it's Bot Turn and if id is not in thread_list (prevent multiple threads on same game)
                    if board_event['isMyTurn'] and game_id not in list_playing_id:
                        list_playing_id.append(game_id)
                        fen = event['game']['fen']
                        elo_opponent = event['game']['opponent']['rating']
                        print('My turn')
                        game_thread = threading.Thread(target=handle_game_bot_turn, args=(game_id, fen, elo_opponent))
                        game_threads.append(game_thread)
                        game_thread.start()
                print('Finish events loop')
                time.sleep(5)
                return
        except berserk.exceptions.ResponseError as e:
            print(f"Rate limit exceeded: {e}. Waiting before retrying...")
            time.sleep(90)  # Wait for 90 seconds before retrying
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(10)  # Wait for 10 seconds before retrying

    while True:
        print('While..')
        handle_events()
        # Clean up finished game threads
        game_threads = [thread for thread in game_threads if thread.is_alive()]
        time.sleep(30)  # Adjust the sleep time as needed
        main()

if __name__ == "__main__":
    main()