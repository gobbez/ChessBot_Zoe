import berserk
import yaml
import chess
import random
import pandas as pd
import threading
import time

import read_fen_database


# Load configuration from file config.yml
with open('config.yml', 'r') as config_file:
    config = yaml.safe_load(config_file)

# Configure Lichess client with token
session = berserk.TokenSession(config['token'])
client = berserk.Client(session=session)


def handle_game_bot_turn(game_id, fen):
    """
    This function handles the moves on Lichess and saves moves.
    :param game_id: the game id that the bot is currently playing
    :param fen: the fen position, to pass to read_fen_database to extract move
    """
    chess_board = chess.Board()
    move_number = 1  # Initialize move number

    for event in client.bots.stream_game_state(game_id):
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
        # Save moves in a DataFrame
        df_moves = pd.DataFrame({'white': list_white, 'black': list_black})
        print(df_moves)

        if len(moves) == 0:
            # First move
            if chess_board.turn == chess.WHITE:
                initial_move = 'g2g3'
            else:
                initial_move = 'g7g6'
            client.bots.make_move(game_id, initial_move)
            chess_board.push_uci(initial_move)
        else:
            # Search for fen
            next_move = read_fen_database.search_fen_in_zst(fen)

            # if next_move found, then use it. Else try a random move
            if next_move:
                client.bots.make_move(game_id, next_move.uci())
                chess_board.push(next_move)
            else:
                list_legal_moves = list(chess_board.legal_moves)
                rand_move = list_legal_moves[random.randint(0, len(list_legal_moves) - 1)]
                client.bots.make_move(game_id, rand_move.uci())
                chess_board.push(rand_move)
        return


def main():
    game_threads = []

    def handle_events():
        try:
            events = client.bots.stream_incoming_events()

            for event in events:
                if event['type'] == 'challenge':
                    if not event['challenge']['rated']:
                        # Accepting only unrated games for now
                        challenge_id = event['challenge']['id']
                        client.bots.accept_challenge(challenge_id)

                elif event['type'] == 'gameStart':
                    fen = event['game']['fen']
                    board_event = event['game']
                    if board_event['isMyTurn']:
                        game_id = event['game']['id']
                        game_thread = threading.Thread(target=handle_game_bot_turn, args=(game_id, fen))
                        game_threads.append(game_thread)
                        game_thread.start()

                return

        except:
            print("Rate limit exceeded. Waiting before retrying...")
            time.sleep(90)  # Wait for 90 seconds before retrying

    while True:
        handle_events()
        # Clean up finished game threads
        game_threads = [thread for thread in game_threads if thread.is_alive()]
        time.sleep(5)  # Adjust the sleep time as needed
        print('Here')
        main()


if __name__ == "__main__":
    main()
