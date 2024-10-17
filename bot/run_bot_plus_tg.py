import berserk
import asyncio
import yaml
import chess
import chess.engine
import chess.pgn
import random
import pandas as pd
import threading
import time
from pathlib import Path
import ollama
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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

# global variable to stop while if Stockfish is thinking (1 = stop while)
bot_thinking = 0

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
    :param search_for: str to tell what column to access (Level, Think or Wait_Api)
    :param game_for: value to access if a particular opponent or game to set params
    :param action: set or get
    :param add_value: value to be set
    :return: DataFrame to access modified params
    """
    # Set level from Telegram db
    global_csv = THIS_FOLDER / "database/Set_Stockfish.csv"
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
                set_wait = df_global['Wait_Api'][0]
                return set_wait
    elif action == 'set':
        if game_for == 'global':
            if search_for == 'level':
                df_global.loc[df_global['Game'] == game_for, 'Level'] = add_value
                df_global.to_csv(global_csv)
            elif search_for == 'think':
                df_global.loc[df_global['Game'] == game_for, 'Think'] = add_value
                df_global.to_csv(global_csv)
            elif search_for == 'hash':
                df_global.loc[df_global['Game'] == game_for, 'Hash'] = add_value
                df_global.to_csv(global_csv)
            elif search_for == 'depth':
                df_global.loc[df_global['Game'] == game_for, 'Depth'] = add_value
                df_global.to_csv(global_csv)
            elif search_for == 'thread':
                df_global.loc[df_global['Game'] == game_for, 'Thread'] = add_value
                df_global.to_csv(global_csv)
            elif search_for == 'wait_api':
                df_global.loc[df_global['Game'] == game_for, 'Wait_Api'] = add_value
                df_global.to_csv(global_csv)


# Lichess Analysis Move
def lichess_analysis_move(fen, game_pgn, tot_moves, game_id):
    """
    Connects to Lichess Analysis Board, filters for >2500 Lichess users and play the most played move
    :param fen: fen position
    :param game_pgn: pgn of game
    :param tot_moves: total numbers played in the game
    :param game_id: id of the game
    :return: the most played move (if any), number of times that move is played, avg_rating of played moves
    """
    # Set up Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Initialize the driver with the specified options
    driver = webdriver.Chrome(options=chrome_options)

    # Go to Analysis Board
    link = f'https://lichess.org/analysis'
    driver.get(link)
    try:
        # Write PGN in Lichess Analysis
        game_pgn = str(game_pgn)
        write_pgn = driver.find_element(By.CSS_SELECTOR, "textarea.copyable")
        write_pgn.click()
        write_pgn.send_keys(game_pgn)
        driver.find_element(By.CSS_SELECTOR,"button.button.button-thin.bottom-item.bottom-action.text[data-icon='']").click()
        # Click on "book icon"
        driver.find_element(By.CLASS_NAME, 'fbt').click()
        # Get Opening Name and tell it if it's 3rd move
        if 1 < tot_moves < 10:
            print(tot_moves)
            # driver.find_element(By.CLASS_NAME,'message').click()
            # Click on move tot_moves to get Opening name
            move_xpath = f"//index[text()='{tot_moves}']/following-sibling::move"
            print('ok found move number')
            move_element = driver.find_element(By.XPATH, move_xpath)
            move_element.click()
            print('ok click on move number')
            time.sleep(2)
            title_element = driver.find_element(By.CLASS_NAME, "title")
            title_text = title_element.get_attribute("title")
            print('ok get title opening')
            # Send message to Lichess Chat
            message = f"We are playing this Opening: {title_text}"
            client.bots.post_message(game_id, message, False)
            run_telegram_bot.send_message_to_telegram(telegram_token, message)
            # Go to last move
            move_xpath = "//index[last()]/following-sibling::move[last()]"
            move_element = driver.find_element(By.XPATH, move_xpath)
            move_element.click()
        # Click on Lichess players
        time.sleep(1)
        driver.find_element(By.XPATH, '//button[contains(@class, "button-link") and text()="Lichess"]').click()
        # Open filter settings
        driver.find_element(By.CLASS_NAME, 'toconf').click()
        # Select only rapid and longer (de-select bullet and blitz)
        driver.find_element(By.XPATH, '//button[@title="Bullet"]').click()
        driver.find_element(By.XPATH, '//button[@title="Blitz"]').click()
        # Select only >2200 elo
        for i in ['1000', '1200', '1400', '1600', '1800', '2000', '2200']:
            driver.find_element(By.XPATH, f'//button[text()={i}]').click()
        # Confirm
        driver.find_element(By.XPATH, '//button[@class="button button-green text" and @data-icon=""]').click()
        # Find element <tr> with data-uci="move"
        get_move = driver.find_element(By.XPATH, '//tbody[@data-fen]/tr[1]')
        # Find number playing
        get_num_played = driver.find_element(By.XPATH, '//tbody/tr[1]/td[3]').text
        # Find avg rating
        avg_rating = driver.find_element(By.XPATH, '//td[contains(@title, "Punteggio medio")]').get_attribute("title")
        move = get_move.get_attribute('data-uci')
        return move, get_num_played, avg_rating
    except:
        return 0, 0, 0


# OLLAMA CHAT
def ollama_stream_message():
    """
    Ollama Gemma2:2b will read the prompt to write a messages
    :return: AI message
    """
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
    ai_message = stream['message']['content']
    # Get only first 140 characters of the message (Lichess chat is 140 chars max)
    ai_message = ai_message[:141]
    return ai_message


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
    Stockfish analyzes position and finds the best move with its parameters based on opponent_elo
    :param fen: fen position
    :param opponent_elo: elo of opponent
    :return: best move for that thinking time
    """
    global STOCKFISH_PATH

    def get_level_time():
        # Set base level, thinking time, hash memory, move depth and threads_m
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

    # Set the board position
    board = chess.Board(fen)

    # Evaluate position CP to determine how the bot is playing (level, thinking time, hash memory, moves depth, threads)
    cp = evaluate_position_cp(fen)
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
    elif set_hash >= 2100:
        hash_m = 2100
    else:
        hash_m = set_hash

    # Check if shared global var Depth is setted (to modify depth moves from Telegram Bot)
    set_depth = load_global_db('depth', 'global', 'get', 0)
    if set_depth <= 0 or set_depth is None:
        # Not setted
        pass
    elif set_depth >= 30:
        depth = 30
    else:
        depth = set_depth

    # Check if shared global var Thread is setted (to modify threads from Telegram Bot)
    set_thread = load_global_db('thread', 'global', 'get', 0)
    if set_thread <= 0 or set_thread is None:
        # Not setted
        pass
    elif set_thread >= 20:
        threads_m = 20
    else:
        threads_m = set_thread

    # Send message to Telegram Bot
    send_message = (f"Playing against: {opponent_name} -- {opponent_elo}\n"
                    f"CP evaluation: {cp // 100}\n"
                    f"Playing at level: {skill_level}\n"
                    f"Thinking time: {round(deep_time, 1)}s\n"
                    f"Hash Memory: {round(hash_m)}Mb\n"
                    f"Moves Depth: {round(depth)}\n"
                    f"Threads Num: {round(threads_m)}")
    run_telegram_bot.send_message_to_telegram(telegram_token, send_message)

    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
        # Set hash size (in MB)
        engine.configure({"Hash": hash_m})
        # Set the number of threads
        engine.configure({"Threads": threads_m})
        # Set level
        engine.configure({"Skill Level": skill_level})
        result = engine.play(board, chess.engine.Limit(time=deep_time, depth=depth))

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
    global bot_thinking
    chess_board = chess.Board()
    move_number = 1  # Initialize move number

    for event in client.bots.stream_game_state(game_id):
        try:
            print(f"Playing: {event['id']}")
        except:
            print('Impredictable error..')
            return
        if 'state' not in event:
            continue  # Skip this event if it doesn't contain the 'state' key

        # Update the chess board with all moves
        moves = event['state']['moves'].split()
        tot_moves = len(moves)//2
        # Create PGN
        game_pgn = chess.pgn.Game()
        game_pgn.headers["Event"] = f"VS {opponent_name}"
        node = game_pgn
        # Add moves to chessboard and PGN
        for move in moves:
            uci_move = chess.Move.from_uci(move)
            if uci_move in chess_board.legal_moves:
                chess_board.push(uci_move)
                node = node.add_variation(uci_move)
            else:
                print(f"Move {move} is not legal at the current board state.")

        # Read Opening Books before using Stockfish 17
        next_move = read_opening_book(fen)
        try:
            if next_move:
                # Use the move from Opening Books file
                client.bots.make_move(game_id, next_move)
                chess_board.push_uci(next_move)
                print('I moved from Opening Book')
                send_message = f'My move is from a human Opening Repertoire'
                client.bots.post_message(game_id, send_message, False)
                tg_message = f"Playing against: {opponent_name} -- {elo_opponent}\n"
                run_telegram_bot.send_message_to_telegram(telegram_token, tg_message + send_message)
            else:
                # Use Lichess Analysis to find the most played human move and get Opening Name
                next_move, get_number_played, avg_rating = lichess_analysis_move(fen, game_pgn, tot_moves, game_id)
                if next_move != 0:
                    # Move the most played move from Lichess Analysis Board
                    client.bots.make_move(game_id, next_move)
                    chess_board.push_uci(next_move)
                    print('I moved from Lichess Analysis Board')
                    # Get avg_elo correctly
                    if avg_rating[-4].startswith(('1', '2', '3')):
                        avg_rating = avg_rating[-4:]
                    elif avg_rating[-3].startswith(('1', '2', '3')):
                        avg_rating = avg_rating[-3:]
                    send_message = f'My move is a human move that was played {get_number_played} times, with avg Elo: {avg_rating}'
                    client.bots.post_message(game_id, send_message, False)
                    tg_message = f"Playing against: {opponent_name} -- {elo_opponent}\n"
                    run_telegram_bot.send_message_to_telegram(telegram_token, tg_message + send_message)
                else:
                    # Use Stockfish 17 to find best move
                    next_move = stockfish_best_move(fen, elo_opponent, opponent_name)
                    client.bots.make_move(game_id, next_move.uci())
                    chess_board.push(next_move)
                    print('I moved from Stockfish')
                    send_message = f'My move is from Stockfish 17'
                    client.bots.post_message(game_id, send_message, False)
            # Set bot_thinking to 0 so that While iteration can continue
            bot_thinking = 0
            return
        except Exception as e:
            print(f"Invalid move: {e}")
            list_legal_moves = list(chess_board.legal_moves)
            rand_move = list_legal_moves[random.randint(0, len(list_legal_moves) - 1)]
            client.bots.make_move(game_id, rand_move.uci())
            chess_board.push(rand_move)
            print('Invalid move.. i moved random')
            tg_message = f"Playing against: {opponent_name} -- {elo_opponent}\n"
            run_telegram_bot.send_message_to_telegram(telegram_token, tg_message + 'I moved random')
            return


def handle_events():
    global bot_thinking
    game_threads = []
    try:
        while True:
            # Process only if Stockfish isn't thinking a move
            if bot_thinking == 0:
                print('While..')
                counter = 0

                # Get number of active games
                ongoing_games = client.games.get_ongoing()
                active_games = [game for game in ongoing_games]
                active_games_count = len(active_games)

                events = client.bots.stream_incoming_events()
                for event in events:
                    counter += 1
                    if counter < active_games_count:
                        print(event['game']['opponent'])
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
                                # Set bot_thinking to 1 in order to stop While iteration
                                bot_thinking = 1
                                if game_id not in list_playing_id:
                                    list_playing_id.append(game_id)
                                    ai_send_message = ollama_stream_message()
                                    client.bots.post_message(game_id, ai_send_message, False)
                                fen = event['game']['fen']
                                elo_opponent = event['game']['opponent']['rating']
                                opponent_name = event['game']['opponent']['username']
                                print('My turn')
                                game_thread = threading.Thread(target=handle_game_bot_turn,
                                                               args=(game_id, fen, elo_opponent, opponent_name))
                                game_threads.append(game_thread)
                                game_thread.start()
                                print(f'Active Thread number: {threading.active_count()}')
                    else:
                        # Clean up finished game threads
                        game_threads = [thread for thread in game_threads if thread.is_alive()]
                        # Get wait time
                        set_wait = load_global_db('wait_api', 'global', 'get', 0)
                        if set_wait <= 0:
                            print('waiting 15s')
                            time.sleep(15)
                        elif set_wait > 180:
                            print('waiting 180s')
                            time.sleep(180)
                        else:
                            print(f'waiting {set_wait}s')
                            time.sleep(set_wait)
                        # Returns to While
                        counter = 0
                        break

    except berserk.exceptions.ResponseError as e:
        print(f"Rate limit exceeded: {e}. Waiting before retrying...")
        time.sleep(90)  # Wait for 90 seconds before retrying
        handle_events()  # Restart the event handling after the wait
    except Exception as e:
        print(f"Unexpected error: {e}")
        time.sleep(10)  # Wait for 10 seconds before retrying
        handle_events()  # Restart the event handling after the wait


if __name__ == "__main__":
    handle_events()



