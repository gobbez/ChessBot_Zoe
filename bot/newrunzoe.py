import berserk
import asyncio
import yaml
import chess
import chess.engine
import chess.pgn
import chess.variant
import random
import pandas as pd
import threading
import time
from pathlib import Path
import sys
import platform

import run_telegram_bot


# Avoid max recursion limit
sys.setrecursionlimit(100000)
THIS_FOLDER = Path(__file__).parent.resolve()
# Path of Stockfish binary (try both Windows and Linux Paths)
if platform.system() == 'Windows':
    STOCKFISH_PATH = THIS_FOLDER / "stockfish/stockfish-windows-x86-64-avx2.exe"
    FAIRY_STOCKFISH_PATH = THIS_FOLDER / "stockfish/Fairy/Windows/fairy-stockfish-largeboard_x86-64-bmi2.exe"
else:
    STOCKFISH_PATH = THIS_FOLDER / "stockfish/stockfish-ubuntu-x86-64-avx2"
    FAIRY_STOCKFISH_PATH = THIS_FOLDER / "stockfish/Fairy/Linux/fairy-stockfish-largeboard_x86-64-bmi2"

config_path = THIS_FOLDER / "config.yml"
# Ollama chat
df_chat = pd.read_csv(THIS_FOLDER / "database/AIChat.csv")

# global variable to send challenges (input starts from Telegram)
challenge_mode = 0
# Make the bot try 3 times
try_challenge = 0

# List of active games id:
list_playing_id = []

# List of active games with less than 2':
hurry_list = []


# Load configuration from file config.yml
with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

# Configure Lichess client with token
session = berserk.TokenSession(config['token'])
client = berserk.Client(session=session)
# Configure Challenges Lichess client to read challenges only
challenges_session = berserk.TokenSession(config['challenges_token'])
client_challenges = berserk.Client(session=challenges_session)
# Configure Telegram bot with token
telegram_token = config['tg_token']


# Global shared (between Lichess and Telegram Bots) functions
def load_global_db(search_for='', game_for='', action='', add_value=0):
    """
    This csv file will be shared between Lichess and Telegram Bots to set params
    Load the param(s) you are setting
    :param search_for: str to tell what column to access (Level, Think or Wait_Api)
    :param game_for: value to access if a particular opponent or game to set params
    :param action: set or get
    :param add_value: value to be set
    :return: DataFrame to access modified params
    """
    # Set level from Telegram db
    global_csv = THIS_FOLDER / "database/Settings.csv"
    df_global = pd.read_csv(global_csv)
    if action == 'get':
        if game_for == 'global':
            df_global = df_global[df_global['Game'] == game_for]
            if search_for == 'level' and len(df_global) == 1:
                return df_global['Level'][0]
            elif search_for == 'think' and len(df_global) == 1:
                return df_global['Think'][0]
            elif search_for == 'hash' and len(df_global) == 1:
                return df_global['Hash'][0]
            elif search_for == 'depth' and len(df_global) == 1:
                return df_global['Depth'][0]
            elif search_for == 'thread' and len(df_global) == 1:
                return df_global['Thread'][0]
            elif search_for == 'wait_api' and len(df_global) == 1:
                return df_global['Wait_Api'][0]
            elif search_for == 'challenge_loops' and len(df_global) == 1:
                return df_global['Challenge_Loops'][0]
            elif search_for == 'challenge_time' and len(df_global) == 1:
                return df_global['Challenge_Time'][0]
            elif search_for == 'challenge_increment' and len(df_global) == 1:
                return df_global['Challenge_Increment'][0]
            elif search_for == 'challenge_opp_elo' and len(df_global) == 1:
                return df_global['Challenge_Opponent_Elo'][0]
            elif search_for == 'challenge_variant' and len(df_global) == 1:
                return df_global['Challenge_Variant'][0]
    elif action == 'set':
        if game_for == 'global':
            if search_for == 'level':
                df_global.loc[df_global['Game'] == game_for, 'Level'] = add_value
            elif search_for == 'think':
                df_global.loc[df_global['Game'] == game_for, 'Think'] = add_value
            elif search_for == 'hash':
                df_global.loc[df_global['Game'] == game_for, 'Hash'] = add_value
            elif search_for == 'depth':
                df_global.loc[df_global['Game'] == game_for, 'Depth'] = add_value
            elif search_for == 'thread':
                df_global.loc[df_global['Game'] == game_for, 'Thread'] = add_value
            elif search_for == 'wait_api':
                df_global.loc[df_global['Game'] == game_for, 'Wait_Api'] = add_value
            elif search_for == 'challenge_loops':
                df_global.loc[df_global['Game'] == game_for, 'Challenge_Loops'] = add_value
            elif search_for == 'challenge_time':
                df_global.loc[df_global['Game'] == game_for, 'Challenge_Time'] = add_value
            elif search_for == 'challenge_increment':
                df_global.loc[df_global['Game'] == game_for, 'Challenge_Increment'] = add_value
            elif search_for == 'challenge_opp_elo':
                df_global.loc[df_global['Game'] == game_for, 'Challenge_Opponent_Elo'] = add_value
            elif search_for == 'challenge_variant':
                df_global.loc[df_global['Game'] == game_for, 'Challenge_Variant'] = add_value
            # Save csv
            df_global.to_csv(global_csv)


def random_chat():
    """
    Pick a random message of the df_chat (those are generated by AI messages) to send in Lichess chat
    :return: random message
    """
    global df_chat
    chat = df_chat['Intro_message'].to_list()
    send_random_chat = chat[random.randint(0, len(chat))]
    return send_random_chat


def create_challenge(username, ch_time, ch_incr):
    """
    For Telegram only, make the bot challenge the user with the Telegram Bot button
    """
    global try_challenge
    client.challenges.create(username=username,
                             rated=False,
                             clock_limit=ch_time,
                             clock_increment=ch_incr)
    message = f'Challenging USER: {username}'
    print(message)
    run_telegram_bot.send_message_to_telegram(telegram_token, message)
    try_challenge = 0


def send_challenge():
    """
    Automatize Lichess to send challenges to other Bots
    """
    global challenge_mode, try_challenge
    if try_challenge <= 3:
        try:
            set_challenge_time = int(load_global_db('challenge_time', 'global', 'get', 0))
            set_challenge_increment = int(load_global_db('challenge_increment', 'global', 'get', 0))
            set_challenge_oppelo = int(load_global_db('challenge_opp_elo', 'global', 'get', 0))
            set_challenge_variant = load_global_db('challenge_variant', 'global', 'get', 0)
            if set_challenge_time < 180:
                challenge_time = 900
            else:
                challenge_time = set_challenge_time
            if set_challenge_increment <= 0:
                challenge_increment = 14
            else:
                challenge_increment = set_challenge_increment
            if set_challenge_oppelo <= 0:
                challenge_elo = 3000
            else:
                challenge_elo = set_challenge_oppelo

            print(f'Searching for bots with Elo >= {challenge_elo}')
            active_bots = client.bots.get_online_bots()
            list_bots = []
            for bot in active_bots:
                if bot['perfs']['classical']['rating'] >= round(challenge_elo):
                    list_bots.append(bot['username'])

            if list_bots:
                # Challenge a random > 2300 bot on rapid cadence
                rand_bot = random.choice(list_bots)
                client.challenges.create(username=rand_bot,
                                         rated=True,
                                         clock_limit=challenge_time,
                                         clock_increment=challenge_increment,
                                         variant=set_challenge_variant)
                message = f'Challenging: {rand_bot}'
                print(message)
                run_telegram_bot.send_message_to_telegram(telegram_token, message)
                try_challenge = 0
            else:
                print(f"No bots with rating >= {challenge_elo} found.")
        except Exception as e:
            print(f'Error: {e}')
            try_challenge += 1


# STOCKFISH FUNCTIONS
def evaluate_position_cp(fen, variant):
    """
    Analyze the position and returns CP value (int)
    :param fen: fen position
    :param variant: type of chess variant (normal is "standard")
    :return: CP value (int)
    """
    global STOCKFISH_PATH, FAIRY_STOCKFISH_PATH

    # Use Stockfish for standard games and Fairy Stockfish for variants, set boards for each
    if variant == 'standard' or variant == 'chess960' or variant == 'fromPosition':
        path = STOCKFISH_PATH
        board = chess.Board(fen)
    elif variant == 'crazyhouse':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.CrazyhouseBoard(fen)
    elif variant == 'antichess':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.AntichessBoard(fen)
    elif variant == 'atomic':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.AtomicBoard(fen)
    elif variant == 'horde':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.HordeBoard(fen)
    elif variant == 'kingOfTheHill':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.KingOfTheHillBoard(fen)
    elif variant == 'racingKings':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.RacingKingsBoard(fen)
    elif variant == 'threeCheck':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.ThreeCheckBoard(fen)

    with chess.engine.SimpleEngine.popen_uci(path) as engine:
        info = engine.analyse(board, chess.engine.Limit(time=2.0))
        cp = str(info['score'].relative)
        if "#" in cp:
            cp = cp[1:]
            cp = int(cp) * 1000
        else:
            cp = int(cp)
        return cp


def stockfish_best_move(fen, opponent_elo, opponent_name, game_id, variant):
    """
    Stockfish analyzes position and finds the best move with its parameters based on opponent_elo
    :param fen: fen position
    :param opponent_elo / opponent_name: elo and name of opponent
    :param game_id: id of Lichess game
    :param variant: type of chess variant (normal is "standard")
    :return: best move for that thinking time
    """
    global STOCKFISH_PATH, FAIRY_STOCKFISH_PATH

    def get_level_time():
        """
        Set base level, thinking time, hash memory, move depth and threads_m based on Elo
        """
        if opponent_elo <= 700:
            deep_time = 0.2
            skill_level = 2
            hash_m = 16
            depth = 4
            threads_m = 4
        elif opponent_elo <= 1000:
            deep_time = 0.5
            skill_level = 4
            hash_m = 16
            depth = 8
            threads_m = 8
        elif opponent_elo <= 1500:
            deep_time = 1.0
            skill_level = 9
            hash_m = 32
            depth = 10
            threads_m = 11
        elif opponent_elo <= 2000:
            deep_time = 1.5
            skill_level = 14
            hash_m = 128
            depth = 12
            threads_m = 11
        elif opponent_elo <= 2300:
            deep_time = 2.3
            skill_level = 16
            hash_m = 512
            depth = 15
            threads_m = 13
        elif opponent_elo <= 2500:
            deep_time = 5.0
            skill_level = 18
            hash_m = 1028
            depth = 20
            threads_m = 15
        else:
            deep_time = 10.0
            skill_level = 20
            hash_m = 2056
            depth = 25
            threads_m = 18
        return deep_time, skill_level, hash_m, depth, threads_m

    # Use Stockfish for standard games and Fairy Stockfish for variants, set boards for each
    if variant == 'standard' or variant == 'chess960' or variant == 'fromPosition':
        path = STOCKFISH_PATH
        board = chess.Board(fen)
    elif variant == 'crazyhouse':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.CrazyhouseBoard(fen)
    elif variant == 'antichess':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.AntichessBoard(fen)
    elif variant == 'atomic':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.AtomicBoard(fen)
    elif variant == 'horde':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.HordeBoard(fen)
    elif variant == 'kingOfTheHill':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.KingOfTheHillBoard(fen)
    elif variant == 'racingKings':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.RacingKingsBoard(fen)
    elif variant == 'threeCheck':
        path = FAIRY_STOCKFISH_PATH
        board = chess.variant.ThreeCheckBoard(fen)

    if game_id in hurry_list:
        # Make Stockfish move faster, avoiding Telegram interaction, if the id has less than 2'
        deep_time = 1
        hash_m = 2000
        threads_m = 12
        depth = 15
        skill_level = 20
        elo_strength = (skill_level/20 + hash_m/3000 + depth/30 + threads_m/12 + deep_time/20) / 5 * 3200
    else:
        # Standard use. Evaluate position CP to determine Stockfish strength
        cp = evaluate_position_cp(fen, variant)
        deep_time, skill_level, hash_m, depth, threads_m = get_level_time()
        if cp > 800:
            skill_level = 20
        elif 400 < cp <= 600:
            deep_time *= 0.5
            skill_level -= 4
            hash_m *= 0.7
            depth *= 0.6
            threads_m *= 0.7
        elif 100 < cp <= 400:
            deep_time *= 0.7
            skill_level -= 3
            hash_m *= 0.8
            depth *= 0.8
            threads_m *= 0.8
        elif 50 < cp <= 100:
            deep_time *= 0.8
            skill_level -= 2
            hash_m *= 0.9
            depth *= 0.9
            threads_m *= 0.9
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
            hash_m = hash_m * 1.05 + 50
        elif -200 < cp <= -100:
            deep_time *= 2
            skill_level += 3
            hash_m = hash_m * 1.1 + 100
            threads_m *= 1.1
        elif -400 < cp <= -200:
            deep_time *= 4
            skill_level += 5
            hash_m = hash_m * 1.3 + 200
            threads_m *= 1.2
        elif cp < -400:
            deep_time *= 7
            skill_level = 20
            hash_m = hash_m * 1.5 + 300
            threads_m *= 1.4
        if skill_level < 1:
            skill_level = 1
        elif skill_level > 20:
            skill_level = 20
        if threads_m >= 12:
            threads_m = 12
        # Check if a shared global var Level is setted (to modify level from Telegram Bot)
        set_level = load_global_db('level', 'global', 'get', 0)
        if set_level <= 0 or set_level is None:
            # Not setted
            pass
        elif set_level < 0:
            skill_level = 1
        elif set_level > 20:
            skill_level = 20
        else:
            skill_level = set_level
        # Check if shared global var Think is setted (to modify thinking time from Telegram Bot)
        set_think = load_global_db('think', 'global', 'get', 0)
        if set_think <= 0 or set_think is None:
            # Not setted
            pass
        elif set_think >= 3600:
            deep_time = 3600
        else:
            deep_time = set_think
        # Check if shared global var Hash is setted (to modify hash memory from Telegram Bot)
        set_hash = load_global_db('hash', 'global', 'get', 0)
        if set_hash <= 0 or set_hash is None:
            # Not setted
            pass
        elif set_hash >= 5100:
            hash_m = 5100
        else:
            hash_m = set_hash
        # Check if shared global var Depth is setted (to modify depth moves from Telegram Bot)
        set_depth = load_global_db('depth', 'global', 'get', 0)
        if set_depth <= 0 or set_depth is None:
            # Not setted
            pass
        elif set_depth >= 50:
            depth = 50
        else:
            depth = set_depth
        # Check if shared global var Thread is setted (to modify threads from Telegram Bot)
        set_thread = load_global_db('thread', 'global', 'get', 0)
        if set_thread <= 0 or set_thread is None:
            # Not setted
            pass
        elif set_thread >= 12:
            threads_m = 12
        else:
            threads_m = set_thread

        # Estimate Stockfish Elo strength
        try:
            elo_strength = (skill_level/20 + hash_m/3000 + depth/30 + threads_m/12 + deep_time/20) / 5 * 3200
        except:
            elo_strength = 2000

        # Send message to Telegram Bot
        send_message = (f"Playing against: {opponent_name} -- {opponent_elo}\n"
                        f"CP evaluation: {cp // 100}\n"
                        f"Playing at level: {skill_level}\n"
                        f"Thinking time: {round(deep_time, 1)}s\n"
                        f"Hash Memory: {round(hash_m)}Mb\n"
                        f"Moves Depth: {round(depth)}\n"
                        f"Threads Num: {round(threads_m)}\n"
                        f"Playing at: {round(elo_strength)} Elo\n"
                        f"Variant: {variant}")
        run_telegram_bot.send_message_to_telegram(telegram_token, send_message)

    with chess.engine.SimpleEngine.popen_uci(path) as engine:
        # Set hash size (in MB)
        engine.configure({"Hash": hash_m})
        # Set the number of threads
        engine.configure({"Threads": threads_m})
        # Set level
        engine.configure({"Skill Level": skill_level})
        result = engine.play(board, chess.engine.Limit(time=deep_time, depth=depth))
    return result.move, round(elo_strength)


def handle_game_bot_turn(game_id, fen, elo_opponent, opponent_name, variant):
    """
    This function handles the moves on Lichess and saves moves.
    :param game_id: the game id that the bot is currently playing
    :param fen: the fen position, to pass to read_fen_database to extract move
    :param elo_opponent: opponent Lichess elo
    """
    # Set boards for variants or normal ("standard")
    # Use Stockfish for standard games and Fairy Stockfish for variants, set boards for each
    if variant == 'standard' or variant == 'chess960' or variant == 'fromPosition':
        chess_board = chess.Board(fen)
    elif variant == 'crazyhouse':
        chess_board = chess.variant.CrazyhouseBoard(fen)
    elif variant == 'antichess':
        chess_board = chess.variant.AntichessBoard(fen)
    elif variant == 'atomic':
        chess_board = chess.variant.AtomicBoard(fen)
    elif variant == 'horde':
        chess_board = chess.variant.HordeBoard(fen)
    elif variant == 'kingOfTheHill':
        chess_board = chess.variant.KingOfTheHillBoard(fen)
    elif variant == 'racingKings':
        chess_board = chess.variant.RacingKingsBoard(fen)
    elif variant == 'threeCheck':
        chess_board = chess.variant.ThreeCheckBoard(fen)

    for event in client.bots.stream_game_state(game_id):
        try:
            print(f"Playing: {event['id']}")
        except:
            print('Impredictable error..')
            return

        try:
            # Use Stockfish 17 to find best move
            next_move, elo_strength = stockfish_best_move(fen, elo_opponent, opponent_name, game_id, variant)
            client.bots.make_move(game_id, next_move.uci())
            chess_board.push(next_move)
            print(f'I moved from Stockfish at {elo_strength} Elo')
            send_message = f'My move is from Stockfish 17 at {elo_strength} Elo'
            client.bots.post_message(game_id, send_message, False)
            return

        except Exception as e:
            print(f"Invalid move: {e}")
            list_legal_moves = list(chess_board.legal_moves)
            rand_move = list_legal_moves[random.randint(0, len(list_legal_moves) - 1)]
            client.bots.make_move(game_id, rand_move.uci())
            chess_board.push(rand_move)
            print('Invalid move.. i moved random')
            tg_message = f"Playing against: {opponent_name} -- {elo_opponent}\n"
            run_telegram_bot.send_message_to_telegram(telegram_token, tg_message + f'I moved random as {e}')
            return


def handle_single_event(game_id, variant):
    """
    Handle only one event, in another Thread, for game(s) with less than 2'
    """
    countdown = 0
    try:
        while True:
            # If countdown is >= 1000 then close this function and thread
            countdown += 1
            if countdown >= 1000:
                # Remove the id from the list and return 10 (thread is over)
                hurry_list.remove(game_id)
                return 10
            # Stream every game but focus only on the game with < 2 min (game_id)
            events = client.games.get_ongoing()
            for event in events:
                is_bot_turn = event['isMyTurn']
                all_game_id = event['gameId']
                if all_game_id == game_id and is_bot_turn:
                    # This means the thread is still active
                    countdown -= 1
                    # If first move send welcome message
                    if event['hasMoved'] == False:
                        ai_send_message = random_chat()
                        client.bots.post_message(game_id, ai_send_message, False)
                    fen = event['fen']
                    elo_opponent = event['opponent']['rating']
                    opponent_name = event['opponent']['username']
                    print('My turn')
                    handle_game_bot_turn(game_id, fen, elo_opponent, opponent_name, variant)
    except berserk.exceptions.ResponseError as e:
        print(f"Rate limit exceeded: {e}. Waiting before retrying...")
        tg_message = f"Rate limit exceeded: {e}. Waiting before retrying..."
        run_telegram_bot.send_message_to_telegram(telegram_token, tg_message + 'I moved random')
        hurry_list.remove(game_id)
        return 10
    except Exception as e:
        print(f"Unexpected error: {e}")
        tg_message = f"Unexpected error: {e}"
        run_telegram_bot.send_message_to_telegram(telegram_token, tg_message + 'I moved random')
        hurry_list.remove(game_id)
        return 10


def handle_events():
    """
    Most important function. Loops each active game on Lichess and handle moves and threads
    """
    counter_challenge = 0
    try:
        while True:
            counter_challenge += 1

            set_challenge_loops = load_global_db('challenge_loops', 'global', 'get', 0)
            if set_challenge_loops < 100:
                challenge_loops = 2000
            else:
                challenge_loops = set_challenge_loops
            print(f'While loop num: {counter_challenge} -- challenge is at: {challenge_loops}')
            if counter_challenge > challenge_loops:
                counter_challenge = 0
                send_challenge()

            # Check challenges
            if challenge_loops % 5 == 0:
                check_challenges()
                pass

            # Stream every games
            events = client.games.get_ongoing()
            for event in events:
                is_bot_turn = event['isMyTurn']
                game_id = event['gameId']
                variant = event['variant']['key']

                try:
                    if event['secondsLeft'] <= 120 and is_bot_turn and game_id not in hurry_list:
                        # If game has < 2' secondsLeft create a thread just for it
                        thread = threading.Thread(target=handle_single_event, args=(game_id, variant))
                        if thread == 10:
                            # 10 means the function in the thread is finished, so it can close this session
                            break
                        thread.start()
                        hurry_list.append(game_id)
                        continue
                except:
                    pass

                print(game_id)

                # Check if it's Bot Turn and if it's not in the other Thread
                if game_id not in hurry_list:
                    if is_bot_turn:
                        # If first move send welcome message
                        if event['hasMoved'] == False:
                            ai_send_message = random_chat()
                            client.bots.post_message(game_id, ai_send_message, False)
                        fen = event['fen']
                        elo_opponent = event['opponent']['rating']
                        opponent_name = event['opponent']['username']
                        print('My turn')
                        handle_game_bot_turn(game_id, fen, elo_opponent, opponent_name, variant)

    except berserk.exceptions.ResponseError as e:
        print(f"Rate limit exceeded: {e}. Waiting before retrying...")
        tg_message = f"Rate limit exceeded: {e}. Waiting before retrying..."
        run_telegram_bot.send_message_to_telegram(telegram_token, tg_message + 'I moved random')
        time.sleep(10)  # Wait for 90 seconds before retrying
        handle_events()  # Restart the event handling after the wait
    except Exception as e:
        print(f"Unexpected error: {e}")
        tg_message = f"Unexpected error: {e}"
        run_telegram_bot.send_message_to_telegram(telegram_token, tg_message + 'I moved random')
        time.sleep(10)  # Wait for 10 seconds before retrying
        handle_events()  # Restart the event handling after the wait


def check_challenges():
    """
    Check challenges and accept them if the cadence times are met
    """
    challenges = client_challenges.challenges.get_mine()
    for challenge in challenges['in']:
        print(challenge)
        challenger = challenge['challenger']['id']
        try:
            challenge_cadence = challenge['speed']
        except:
            challenge_cadence = challenge['timeControl']['type']
        challenge_id = challenge['id']
        variant = challenge['variant']['key']

        try:
            if variant == 'standard':
                # Challenge standard
                if challenge_cadence == 'correspondence' and challenge['timeControl']['type'] != 'unlimited':
                    client.bots.accept_challenge(challenge_id)
                    print(f"New Challenger: {challenger} on {challenge_cadence}")
                elif (challenge['timeControl']['limit'] >= 900 and challenge['timeControl']['increment'] >= 14) or \
                        challenge['speed'] == 'standard':
                    client.bots.accept_challenge(challenge_id)
                    print(f"New Challenger: {challenger} on {challenge_cadence}")
                else:
                    client.bots.decline_challenge(challenge_id=challenge_id, reason='tooFast')
            else:
                # Challenge variants
                if challenge['timeControl']['limit'] >= 120 and challenge['timeControl']['type'] != 'unlimited':
                    client.bots.accept_challenge(challenge_id)
                    print(f"New Challenger: {challenger} on {challenge_cadence}")
                else:
                    client.bots.decline_challenge(challenge_id=challenge_id, reason='generic')

        except:
            client.bots.decline_challenge(challenge_id=challenge_id, reason='later')


if __name__ == "__main__":
    handle_events()