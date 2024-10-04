import zstandard as zstd
import json
import io
from pathlib import Path
import numpy as np
import pandas as pd


# File paths
THIS_FOLDER = Path(__file__).parent.resolve()
file_path = THIS_FOLDER / "database/lichess_db_eval.jsonl.zst"
csv_path = THIS_FOLDER / "database/98millionmoves.csv"


def extract_fen():
    """
    Decompress the zst file (with 98m chess positions and evaluations) and extract 2m fens
    :return: pd Dataframe with fens, evaluation and best move
    """
    try:
        df_moves = pd.read_csv(csv_path)
        print('DataFrame found.')
    except:
        print('DataFrame not found. Proceed to creating it')
        with open(file_path, 'rb') as compressed_file:
            dctx = zstd.ZstdDecompressor()
            decompressed = dctx.stream_reader(compressed_file)
            text_stream = io.TextIOWrapper(decompressed, encoding='utf-8')

            # Ask how many extractions to do
            extract_for = input('Write how many moves to extract (type max to extract the whole file): ')
            try:
                if extract_for == 'max':
                    extract_for = 99999999999999999999999999999999999999999999999
                    print(f'Extract until the end of the file (98 millions)')
                else:
                    extract_for = int(extract_for)
                    print(f'Extract for: {extract_for}')
            except:
                print('Wrong input, extract for: 1000')
                extract_for = 1000
            count = 0
            list_fen = []
            list_eval = []
            list_bestmove = []
            for line in text_stream:
                if count <= extract_for:
                    count += 1
                    print(count)
                    record = json.loads(line)

                    # Save results
                    list_fen.append(record['fen'])
                    # Safely access 'cp' or 'mate' key using .get()
                    eval_info = record.get('evals', [{}])[0].get('pvs', [{}])[0]
                    if 'cp' in eval_info:
                        list_eval.append(eval_info['cp'])
                    elif 'mate' in eval_info:
                        mate_value = eval_info['mate']
                        # Convert mate to a high positive or negative value
                        if mate_value > 0:
                            list_eval.append(10000 - mate_value)
                        else:
                            list_eval.append(-10000 - mate_value)
                    # Get 'line' (best move) from eval_info and take only first move
                    list_bestmove.append(eval_info['line'][:4])

                else:
                    # Convert in pd DataFrame and save it as csv
                    df_moves = pd.DataFrame({'Fen': list_fen, 'Eval': list_eval, 'Move': list_bestmove})
                    df_moves.to_csv('98millionmoves.csv')
                    print(df_moves.head())
                    break

    return df_moves


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
    print(search_fen)
    df_single_move = df_moves[df_moves['Fen'].str.contains(search_fen)]

    print("Found Moves:")
    print(df_single_move)


df_move = extract_fen()
search_fen_from_csv(df_move, 'rnbqkbnr/ppp1pppp/8/3p4/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 2')