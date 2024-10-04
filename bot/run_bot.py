import berserk
import yaml
import chess
import random
import pandas as pd
import threading
import time
from pathlib import Path

# Load df
THIS_FOLDER = Path(__file__).parent.resolve()
start_time = time.time()
path_df_100k = THIS_FOLDER / "database/100thousandsmoves.csv"
df_move_100k = pd.read_csv(path_df_100k)
print(f'Loaded df_move_100k in {round(time.time() - start_time)} s')
start_time = time.time()
path_df_2m = THIS_FOLDER / "database/2millionmoves.csv"
df_move_2m = pd.read_csv(path_df_2m)
print(f'Loaded df_move_2m in {round(time.time() - start_time)} s')
start_time = time.time()
path_df_10m = THIS_FOLDER / "database/10millionmoves.csv"
df_move_10m = pd.read_csv(path_df_10m)
print(f'Loaded df_move_10m in {round(time.time() - start_time)} s')
""" Comment since 98 millions parameter is too slow
start_time = time.time()
path_df_98m = THIS_FOLDER / "database/98millionmoves.csv"
df_move_98m = pd.read_csv(path_df_98m)
print(f'Loaded path_df_98m in {round(time.time() - start_time)} s')"""
# List of active games id:
list_playing_id = []


# Load configuration from file config.yml
with open('config.yml', 'r') as config_file:
    config = yaml.safe_load(config_file)

# Configure Lichess client with token
session = berserk.TokenSession(config['token'])
client = berserk.Client(session=session)


def search_fen_from_csv(df_moves, fen):
    """
    Search the best move from the csv file passing its fen
    :param df_moves: DataFrame to pass
    :param fen: FEN position of the game
    :return: best move
    """
    # Search for FEN
    parts = fen.split(' ')
    search_fen = ' '.join(parts[:2])

    # Loop and get only first match
    count_search = 0
    count_thousands = 0
    for index, row in df_moves.iterrows():
        count_search += 1
        if count_search > 9999:
            count_thousands += 1
            print(count_thousands * 10000)
            count_search = 0

        if search_fen in row['Fen']:
            return row['Move']

    # If no match is found, return None
    return None


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
        print(event['id'])
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
            # Search for fen using dataset based on opponent Elo
            if elo_opponent < 1000:
                next_move = search_fen_from_csv(df_move_100k, fen)
                print(f'Searched 100k, next_move: {next_move}')
            elif elo_opponent < 1500:
                next_move = search_fen_from_csv(df_move_2m, fen)
                print(f'Searched 2m, next_move: {next_move}')
            else:
                next_move = search_fen_from_csv(df_move_10m, fen)
                print(f'Searched 10m, next_move: {next_move}')
            # if next_move found, then use it. Else try a random move
            if next_move:
                try:
                    uci_move = chess.Move.from_uci(next_move)
                    client.bots.make_move(game_id, uci_move.uci())
                    print('I moved')
                    chess_board.push(next_move)
                    print('Move found, i moved')
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
                if event['type'] == 'challenge':
                    if not event['challenge']['rated']:
                        print('Challenge accepted!')
                        # Accepting only unrated games for now
                        challenge_id = event['challenge']['id']
                        client.bots.accept_challenge(challenge_id)

                elif event['type'] == 'gameStart':
                    board_event = event['game']
                    game_id = event['game']['id']
                    # Check if it's Bot Turn and check if the id is not there (to prevent to open multiple threads)
                    if board_event['isMyTurn'] and game_id not in list_playing_id:
                        list_playing_id.append(game_id)
                        fen = event['game']['fen']
                        elo_opponent = event['game']['opponent']['rating']
                        print('My turn - got id, fen and elo_opponent')
                        game_thread = threading.Thread(target=handle_game_bot_turn, args=(game_id, fen, elo_opponent))
                        game_threads.append(game_thread)
                        game_thread.start()
                        print('Finish thread')
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
        time.sleep(40)  # Adjust the sleep time as needed
        main()

if __name__ == "__main__":
    main()