
def bot_can_capture(chess_board, move, bot_color, sacrifice='No'):
    """
    Check if bot can capture in that move
    :param chess_board: board
    :param move: move to play
    :param bot_color: bot color
    :param sacrifice: piece that bot is willing to give for that move (default 'No')
    :return: True if conditions are met, meaning bot can capture with that move
    """
    chess_board.push(move)
    bot_attackers = chess_board.attackers(bot_color, move)
    if bot_attackers > 1:
        # Check which piece bot is willing to give
        if sacrifice == 'Queen':
            # Accept since bot want to sacrifice highest piece and >1 moves so no check risk
            chess_board.pop()
            return True

        # Check bot attacker pieces
        attackers = []
        for attacker in bot_attackers:
            attackers.append(chess_board.piece_at(attacker))
            if sacrifice == 'Rook':
                # Accept if there is at least a Rook or smaller piece
                if attacker != 'chess.QUEEN':
                    chess_board.pop()
                    return True
            elif sacrifice == 'Bishop' or sacrifice == 'Knight':
                # Accept if there is at least a Bishop/Knight or smaller piece
                if attacker not in ('chess.QUEEN', 'chess.ROOK'):
                    chess_board.pop()
                    return True
            elif sacrifice == 'Pawn':
                # Accept only if there is Pawn
                if attacker == 'chess.PAWN':
                    chess_board.pop()
                    return True
    chess_board.pop()
    return False



def check_enemy_discovered_attack(chess_board, move, bot_color, enemy_color):
    """
    Check if next move loses a more important bot piece, without be able to recapture back. Else play it
    :param chess_board: board
    :param move: move played by bot, check if it discovers a more important piece of its
    :param bot_color: bot color
    :param enemy_color: opponent color
    :return: True if it's safe or can recapture, False if it loses a more important piece
    """
    chess_board.push(move)
    # If bot discovers its Queen, can accept only if it can recapture back and it's the enemy Queen
    queen_square = chess_board.pieces(chess.QUEEN, bot_color)
    queen_position = [chess.square_name(square) for square in queen_square]
    if queen_position:
        enemy_attackers = chess_board.attackers(enemy_color, queen_position)
        if enemy_attackers == 1:
            # Check if it's a Queen trade
            enemy_piece = chess_board.piece_at(enemy_attackers[0])
            if enemy_piece == 'chess.QUEEN':
                # Accepts if bot can capture back
                accept_bot_capture = bot_can_capture(chess_board, enemy_attackers[0], bot_color, 'Queen')
                if accept_bot_capture:
                    chess_board.pop()
                    return True
                else:
                    chess_board.pop()
                    return False
        if enemy_attackers > 1:
            # Opponent may have another piece attacking queen, so change move
            chess_board.pop()
            return False
    # If bot discovers its Rook, can accept it if it can recapture it and it's the enemy Queen or Rook
    rook_square = chess_board.pieces(chess.ROOK, bot_color)
    rook_position = [chess.square_name(square) for square in rook_square]
    if rook_position:
        enemy_attackers = chess_board.attackers(enemy_color, rook_position)
        if enemy_attackers == 1:
            # Check if it's a Rook trade or better
            enemy_piece = chess_board.piece_at(enemy_attackers[0])
            if enemy_piece in ('chess.QUEEN', 'chess.ROOK'):
                # Accepts if bot can capture back
                accept_bot_capture = bot_can_capture(chess_board, enemy_attackers[0], bot_color, 'Rook')
                if accept_bot_capture:
                    chess_board.pop()
                    return True
                else:
                    chess_board.pop()
                    return False
            else:
                # Don't waste Rook for a minor piece
                chess_board.pop()
                return False
        if enemy_attackers > 1:
            # Check if it's rook(s) and/or queen
            list_enemy_pieces = []
            for enemy in enemy_attackers:
                enemy_piece = chess_board.piece_at(enemy)
                list_enemy_pieces.append(enemy_piece)
            if list_enemy_pieces in ('chess.QUEEN', 'chess.ROOK'):
                # Accepts if bot can capture back
                accept_bot_capture = bot_can_capture(chess_board, enemy_attackers[0], bot_color, 'Rook')
                if accept_bot_capture:
                    chess_board.pop()
                    return True
                else:
                    chess_board.pop()
                    return False
            else:
                # Don't waste Rook for a minor piece
                chess_board.pop()
                return False
    # If bot discovers its Bishop/Knight, can accept it if it can recapture it and it's a more important piece
    bishop_square = chess_board.pieces(chess.BISHOP, bot_color)
    bishop_position = [chess.square_name(square) for square in bishop_square]
    if bishop_position:
        enemy_attackers = chess_board.attackers(enemy_color, bishop_position)
        if enemy_attackers == 1:
            # Check if it's a Bishop/Knight trade or better
            enemy_piece = chess_board.piece_at(enemy_attackers[0])
            if enemy_piece != 'chess.PAWN':
                # Accepts if bot can capture back
                accept_bot_capture = bot_can_capture(chess_board, enemy_attackers[0], bot_color, 'Bishop')
                if accept_bot_capture:
                    chess_board.pop()
                    return True
                else:
                    chess_board.pop()
                    return False
            else:
                # Don't waste Bishop/Knight for a pawn
                chess_board.pop()
                return False
        if enemy_attackers > 1:
            # Check if it's a Bishop/Knight or better
            list_enemy_pieces = []
            for enemy in enemy_attackers:
                enemy_piece = chess_board.piece_at(enemy)
                list_enemy_pieces.append(enemy_piece)
            if list_enemy_pieces not in ('chess.PAWN'):
                # Accepts if bot can capture back
                accept_bot_capture = bot_can_capture(chess_board, enemy_attackers[0], bot_color, 'Bishop')
                if accept_bot_capture:
                    chess_board.pop()
                    return True
                else:
                    chess_board.pop()
                    return False
            else:
                # Don't waste Bishop/Knight for a pawn
                chess_board.pop()
                return False
    # If bot discovers its Bishop/Knight, can accept it if it can recapture it and it's a more important piece
    knight_square = chess_board.pieces(chess.KNIGHT, bot_color)
    knight_position = [chess.square_name(square) for square in knight_square]
    if knight_position:
        enemy_attackers = chess_board.attackers(enemy_color, knight_position)
        if enemy_attackers == 1:
            # Check if it's a Bishop/Knight trade or better
            enemy_piece = chess_board.piece_at(enemy_attackers[0])
            if enemy_piece != 'chess.PAWN':
                # Accepts if bot can capture back
                accept_bot_capture = bot_can_capture(chess_board, enemy_attackers[0], bot_color, 'Knight')
                if accept_bot_capture:
                    chess_board.pop()
                    return True
                else:
                    chess_board.pop()
                    return False
            else:
                # Don't waste Bishop/Knight for a pawn
                chess_board.pop()
                return False
        if enemy_attackers > 1:
            # Check if it's a Bishop/Knight or better
            list_enemy_pieces = []
            for enemy in enemy_attackers:
                enemy_piece = chess_board.piece_at(enemy)
                list_enemy_pieces.append(enemy_piece)
            if list_enemy_pieces not in ('chess.PAWN'):
                # Accepts if bot can capture back
                accept_bot_capture = bot_can_capture(chess_board, enemy_attackers[0], bot_color, 'Knight')
                if accept_bot_capture:
                    chess_board.pop()
                    return True
                else:
                    chess_board.pop()
                    return False
            else:
                # Don't waste Bishop/Knight for a pawn
                chess_board.pop()
                return False
    # If bot discovers its Pawn, can accept it if it can recapture it with Pawn
    pawn_square = chess_board.pieces(chess.PAWN, bot_color)
    pawn_position = [chess.square_name(square) for square in pawn_square]
    if pawn_position:
        # Accepts if bot can capture back with Pawn
        accept_bot_capture = bot_can_capture(chess_board, enemy_attackers[0], bot_color, 'Pawn')
        if accept_bot_capture:
            chess_board.pop()
            return True
        else:
            chess_board.pop()
            return False

    chess_board.pop()
    return False


def human_chess_logic(chess_board, bot_color):
    critical = 0
    # List legal moves
    list_legal_moves = chess_board.legal_moves

    if bot_color == 'White':
        enemy_color = 'Black'
    else:
        enemy_color = 'White'

    # Check if bot is in check
    if chess_board.is_check():
        critical += 99
        # Bot king position
        bot_king = chess_board.king(bot_color)
        bot_king_square = chess.square_name(bot_king)
        # Enemy pieces giving check
        list_enemy_attacking_king = chess_board.attackers(enemy_color, bot_king_square)
        if len(list_enemy_attacking_king) > 1:
            # Bot is under double check. Only way is move king (list_legal_moves)
            for move in list_legal_moves:
                # Check if next move put king in check again, if not play it
                chess_board.push(move)
                is_king_in_check = chess_board.is_check()
                chess_board.pop()
                if not is_king_in_check:
                    return move
        elif len(list_enemy_attacking_king) == 1:
            # Get bot pieces that can attack enemy piece(s) giving check
            list_bot_attacking_enemy_checkers = chess_board.attackers(bot_color, list_enemy_attacking_king[0])
            # If bot has only one move, it must do it
            if len(list_bot_attacking_enemy_checkers) == 1:
                return list_bot_attacking_enemy_checkers[0]
            # If bot can attack enemy piece(s) checking the bot, check risks and the piece bot is using
            for move in list_bot_attacking_enemy_checkers:
                bot_piece = chess_board.piece_at(move)
                accept = check_enemy_discovered_attack(chess_board, move, bot_color, enemy_color)
                if accept:
                    # Bot pass the discovered_attack risk, now it should check which piece use (minor = better)
                    if bot_piece == 'chess.PAWN':
                        # Using a Pawn to capture without risk is better
                        return move
                        # *** CHECK OTHER PIECES ***

    """# *** OTHER THINGS ***
    if not is_king_in_check:

    # Extract the starting position of pieces
    for square in chess.SQUARES:
        piece = chess_board.piece_at(square)
        if piece:
            color = piece.color
            piece_type = piece.piece_type

    list_my_pieces_squares =
    # gives_check(move)"""