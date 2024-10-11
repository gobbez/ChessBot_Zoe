import berserk
import asyncio
import yaml
import chess
import chess.engine
import random
import pandas as pd
import threading
import time
from pathlib import Path
import ollama
import sys

import run_telegram_bot


# Avoid max recursion limit
sys.setrecursionlimit(100000)

# Load Stockfish
THIS_FOLDER = Path(__file__).parent.resolve()
# Path to your Stockfish binary
STOCKFISH_PATH = THIS_FOLDER / "stockfish/stockfish-windows-x86-64-avx2.exe"
config_path = THIS_FOLDER / "config.yml"
# Opening Books
king_gambit_path = THIS_FOLDER / "database/ChessOpeningBook_KingGambit_2.csv"


# List of active games id:
list_playing_id = []


# Load configuration from file config.yml
with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

# Configure Lichess client with token
session = berserk.TokenSession(config['token'])
client = berserk.Client(session=session)

# Configure Telegram bot with token
telegram_token = config['tg_token']


# Global shared (between Lichess and Telegram Bots) functions
def load_global_db(search_for='', game_for='', action='', add_value=0):
    """
    This csv file will be shared between Lichess and Telegram Bots to set params
    Load the param(s) you are setting
    :param search_for: str to tell what column to access
    :param game_for: value to access if a particular opponent or game to set params
    :param action: set or get
    :param add_value: value to be set
    :return: DataFrame to access modified params
    """
    # Set level from Telegram db
    level_csv = THIS_FOLDER / "database/Stockfish_level.csv"
    df_level = pd.read_csv(level_csv)
    if action == 'get':
        set_level = None
        if game_for == 'global':
            df_level = df_level[df_level['Game'] == 'global']
            if search_for == 'level' and len(df_level) == 1:
                set_level = df_level['Level'][0]
                return set_level
    elif action == 'set':
        if game_for == 'global':
            df_level.loc[df_level['Game'] == 'global', 'Level'] = add_value
            df_level.to_csv(level_csv)



# OLLAMA CHAT
def ollama_stream_message():
    ai_prompt = ("You are Zoe, a Lichess chess Bot."
                 "Here's the list of your functions:"
                 "-Chess Books to follow human openings"
                 "-Stockfish 17 to find best move (but your thinking time will vary based on opponent Elo and position)"
                 "You identify as a dog (female) and your owner is andreagobbez")
    intro_prompt = ("Say an intro message. Be funny and cordial and finish with a bark or a woof!"
                    "FORCED TO WRITE LESS THAN 20 WORDS")
    stream = ollama.chat(
        model='gemma2:2b',
        messages=[{'role': 'user', 'content': ai_prompt + intro_prompt}],
    )
    print(stream['message']['content'])
    return stream['message']['content']


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


def stockfish_best_move(fen, opponent_elo, opponent_name):
    """
    Stockfish analyzes position and finds the best move with the thinking time and strength level based on opponent_elo
    :param fen: fen position
    :param opponent_elo: elo of opponent
    :return: best move for that thinking time
    """
    global STOCKFISH_PATH

    def get_level_time():
        # Get the best move
        if opponent_elo <= 700:
            deep_time = 0.2
            skill_level = 2
        elif opponent_elo <= 1000:
            deep_time = 0.5
            skill_level = 4
        elif opponent_elo <= 1500:
            deep_time = 1.0
            skill_level = 9
        elif opponent_elo <= 2000:
            deep_time = 1.5
            skill_level = 14
        elif opponent_elo <= 2300:
            deep_time = 2.3
            skill_level = 16
        elif opponent_elo <= 2500:
            deep_time = 5.0
            skill_level = 18
        else:
            deep_time = 10.0
            skill_level = 20
        return deep_time, skill_level

    # Set the board position
    board = chess.Board(fen)

    # Evaluate position CP to determine how the bot is playing (the worse, the more thinking time)
    cp = evaluate_position_cp(fen)
    deep_time, skill_level = get_level_time()

    if cp > 800:
        skill_level = 20
    elif 400 < cp <= 600:
        deep_time *= 0.5
        skill_level -= 4
    elif 100 < cp <= 400:
        deep_time *= 0.7
        skill_level -= 3
    elif 50 < cp <= 100:
        deep_time *= 0.8
        skill_level -= 2
    elif 0 < cp <= 50:
        deep_time *= 0.9
        skill_level -= 1
    elif cp == 0:
        pass
    elif -50 < cp < 0:
        deep_time *= 1.1
        skill_level += 1
    elif -100 < cp <= 50:
        deep_time *= 1.4
        skill_level += 2
    elif -200 < cp <= -100:
        deep_time *= 2
        skill_level += 3
    elif -400 < cp <= -200:
        deep_time *= 4
        skill_level += 5
    elif cp < -400:
        deep_time *= 7
        skill_level = 20

    if skill_level < 1:
        skill_level = 1
    elif skill_level > 20:
        skill_level = 20

    # Check if a shared global var is setted (to modify level from Telegram Bot)
    set_level = load_global_db('level', 'global', 'get', 0)
    if set_level == 0 or set_level is None:
        # Not setted
        pass
    elif set_level < 0:
        skill_level = 1
    elif set_level > 20:
        skill_level = 20
    else:
        skill_level = set_level

    # Send message to Telegram Bot
    send_message = (f"Playing against: {opponent_name} -- {opponent_elo}\n"
                    f"CP evaluation: {cp // 100}\n"
                    f"Playing at level: {skill_level}\n"
                    f"Thinking time: {deep_time}s")
    run_telegram_bot.send_message_to_telegram(telegram_token, send_message)

    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
        engine.configure({"Skill Level": skill_level})
        result = engine.play(board, chess.engine.Limit(time=deep_time))
        return result.move


def read_opening_book(fen):
    """
    Read the files of Opening and follow them.
    These files are human-made and not the best moves, to give the bot a touch of human-style.
    :param fen: fen of position
    :return: move to play from the book
    """
    df_move = pd.read_csv(king_gambit_path)
    parts = fen.split(' ')
    fen = parts[0]
    df_move = df_move[df_move['Fen'].str.contains(fen)]['Move']
    for move in df_move:
        move = str(move)
        return move


def handle_game_bot_turn(game_id, fen, elo_opponent, opponent_name):
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
            # First move plays fixed moves
            if chess_board.turn == chess.WHITE:
                initial_move = 'e2e4'
            else:
                initial_move = 'g7g6'
            client.bots.make_move(game_id, initial_move)
            chess_board.push_uci(initial_move)
            print('I made first move')
        else:
            # Read Opening Books before using Stockfish 17
            next_move = read_opening_book(fen)
            try:
                if next_move:
                    # Use the move from Opening Books file
                    client.bots.make_move(game_id, next_move)
                    chess_board.push_uci(next_move)
                else:
                    # Use Stockfish 17 to find best move
                    next_move = stockfish_best_move(fen, elo_opponent, opponent_name)
                    client.bots.make_move(game_id, next_move.uci())
                    chess_board.push(next_move)
                    print('I moved')
                return
            except Exception as e:
                print(f"Invalid move: {e}")
                list_legal_moves = list(chess_board.legal_moves)
                rand_move = list_legal_moves[random.randint(0, len(list_legal_moves) - 1)]
                client.bots.make_move(game_id, rand_move.uci())
                chess_board.push(rand_move)
                print('Invalid move.. i moved random')
                return


def main():
    game_threads = []

    def handle_events():
        try:
            events = client.bots.stream_incoming_events()
            for event in events:
                print(event['type'])
                if event['type'] == 'challenge':
                    if event['challenge']['speed'] in ['standard', 'correspondence']:
                        # Accepting only rapid, standard and correspondence games for now (both rated and not)
                        print('Challenge accepted!')
                        # Send message to Telegram Bot
                        send_message = f"Accepted challenge {event}"
                        run_telegram_bot.send_message_to_telegram(telegram_token, send_message)
                        challenge_id = event['challenge']['id']
                        client.bots.accept_challenge(challenge_id)

                elif event['type'] == 'gameStart':
                    board_event = event['game']
                    game_id = event['game']['id']
                    # Check if it's Bot Turn and if id is not in thread_list (prevent multiple threads on same game)
                    if board_event['isMyTurn']:
                        if game_id not in list_playing_id:
                            list_playing_id.append(game_id)
                            ai_send_message = ollama_stream_message()
                            client.bots.post_message(game_id, ai_send_message, False)
                        fen = event['game']['fen']
                        elo_opponent = event['game']['opponent']['rating']
                        opponent_name = event['game']['opponent']['username']
                        print('My turn')
                        game_thread = threading.Thread(target=handle_game_bot_turn, args=(game_id, fen, elo_opponent, opponent_name))
                        game_threads.append(game_thread)
                        game_thread.start()
                        print(f'Active Thread number: {threading.active_count()}')
                print('Finish events loop')
                time.sleep(3)
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
        time.sleep(15)  # Adjust the sleep time as needed
        main()


if __name__ == "__main__":
    main()



