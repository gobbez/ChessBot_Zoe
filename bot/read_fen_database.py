import zstandard as zstd
import json
import io
from pathlib import Path

THIS_FOLDER = Path(__file__).parent.resolve()
file_path = THIS_FOLDER / "github/ChessBot_Zoe/database/lichess_db_eval.jsonl.zst"

def search_fen_in_zst(target_fen):
    """
    Decompress the zst file (with 9m chess positions and evaluations) and search for your fen
    :param file_path: file path
    :param target_fen: fen to search
    :return: dictionary with fen, evaluation and best lines
    """
    with open(file_path, 'rb') as compressed_file:
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.stream_reader(compressed_file)
        text_stream = io.TextIOWrapper(decompressed, encoding='utf-8')

        # Since 98m positions is too much for my pc, i just analyze first 1000000:
        count = 0
        for line in text_stream:
            if count <= 1000000:
                count += 1
                record = json.loads(line)
                if 'fen' in record and record['fen'] == target_fen:
                    return move_extractor(record)
            else:
                return None



def move_extractor(record):
    if 'evals' in record:
        list_cps = record['evals'][0]['pvs']
        # Search for a line of 50 or more cp
        for i in list_cps:
            if i['cp'] >= 50:
                plus_50cp_line = i['line'][0]
                return plus_50cp_line
        # If no such possibile line search for worst line (that will be <50 cp)
        worst_minus_50cp_line = list_cps[-1]['line'][0]
        return worst_minus_50cp_line
        # evals = record['evals'][0]['pvs'][0]['line']
    return None

