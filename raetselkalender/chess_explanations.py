"""Factual explanations generated from moves and engine PVs; legacy audit texts."""
import chess

MOTIFS={
    '01MsO':'Das Schach erzwingt eine Reaktion. In der Beispielvariante öffnet der anschließende En-passant-Schlag die Linien für die Türme und ermöglicht weiteren Materialgewinn.',
    '01Pkt':'Der König sammelt die gegnerischen Bauern ein und unterstützt anschließend einen Freibauern. Seine aktive Stellung entscheidet das Bauernendspiel.',
    '00jCD':'Der Springer verstärkt den Angriff auf den König. Die Abwehr in der Beispielvariante erlaubt es dem Läufer, eine gegnerische Figur zu gewinnen.',
    '02wic':'Der Bauernvorstoß greift den Läufer an. Nach den Abtäuschen in der Beispielvariante kann der andere Läufer zusätzlich Material gewinnen.',
    '017u3':'Der Springer gewinnt mit Schach eine Figur und wird zurückgeschlagen. Der folgende Läuferangriff führt zu einem Qualitätsgewinn: Ein Turm wird gegen eine Leichtfigur gewonnen.',
    '03FPz':'Die Turmschachs lassen der Verteidigung wenig Zeit. In der Beispielvariante wird die Dame gegen einen Turm gewonnen; zusätzlich fällt eine Leichtfigur.',
    '01SN2':'Der König wird aktiv, unterstützt den vorgerückten Freibauern und kann gegnerische Bauern angreifen. Das verbessert die Gewinnchancen im Endspiel entscheidend.',
    '0050w':'Der erste Turmschlag lenkt den verteidigenden Läufer ab. Der zweite Turm setzt mit Schach nach und gewinnt ihn in der Beispielvariante zurück.',
    '01kKD':'Die Dame baut einen gefährlichen Königsangriff auf. In der geprüften Variante helfen auch die gegnerischen Schachs nicht: Die gegnerische Dame wird schließlich vom Turm geschlagen.',
    '02u8i':'Das Springerschach lenkt die Verteidigung ab. Danach wird sogar ein Turm geopfert, um den König freizulegen; der Königsangriff ist hier wichtiger als die kurzfristige Materialbilanz.',
    '03IJa':'Der Turm dringt auf die gegnerische Grundreihe ein. In der Beispielvariante gewinnt er dort einen Turm und sammelt anschließend mit Schach weiteres Material ein.',
    '01FXr':'Das Läuferschach treibt den König ins Mattnetz. In der Beispielvariante setzt die Dame anschließend matt.',
    '036i1':'Der Läufer eröffnet einen Mattangriff. Der in der Beispielvariante dazwischengestellte Verteidiger wird im nächsten Zug mit Matt geschlagen.',
    '03Pky':'Die Dame dringt mit Schach ein. Der König muss ausweichen, worauf die Dame das entscheidende Mattfeld erreicht.',
    '02K8m':'Der Turmzug schafft eine starke Drohung. In der geprüften Variante wird die gegnerische Dame gegen den Turm gewonnen: Nach dem Damenschlag schlägt ein Bauer zurück.',
    '01GBu':'Das Damenopfer lenkt den verteidigenden Turm ab. Danach setzt der zweite Turm auf der Grundreihe matt.',
    '03JeC':'Das Damenopfer zieht den König auf das gewünschte Feld. Der Turm kann anschließend mit Matt eindringen.',
    '01n5R':'Der Bauernschlag gewinnt Material. Die folgende Turmabtauschfolge beseitigt den Vorteil nicht, weil der König selbst zurückschlagen kann.',
    '02PP0':'Das Turmschach zwingt den König zur Reaktion. In der Beispielvariante folgt ein Damentausch mit Schach, danach gewinnt der Turm den gegnerischen Turm auf der Grundreihe.',
    '02fS6':'Der Bauernzug gibt Schach und engt den König ein. Die folgenden Läuferschachs schließen das Mattnetz.',
    '02QYB':'Das Damenopfer mit Schach lenkt einen Bauern ab. Der Turm gewinnt die gegnerische Dame zurück; die zuerst geschlagene Leichtfigur bleibt als Materialgewinn übrig.',
    '00Nte':'Das Damenschach schafft Zeit für weiteren Materialgewinn durch den Läufer. Der anschließende Damentausch vereinfacht die gewonnene Stellung.',
    '03eks':'Das Turmopfer zieht den König aus seiner Deckung. Die Dame nutzt die geöffneten Felder und setzt matt.',
    '02TfH':'Die Dame dringt mit Schach in die Königsstellung ein. Nach dem Ausweichen erreicht sie das gedeckte Mattfeld.',
    '032t1':'Das Turmschach erzwingt eine Antwort. Der dazwischengestellte Turm wird in der Beispielvariante mit Matt geschlagen.',
    '01BeL':'Das Damenopfer erzwingt einen Bauernschlag und öffnet den Angriff auf den König. Nach dem Zurückschlagen vollendet der Turm das Mattnetz.',
    '02IqG':'Das Turmopfer lockt den König an den Rand. Die Dame setzt mit Schach nach und erreicht das Mattfeld.',
    '03JMe':'Die Schachfolge treibt den König auf die Grundreihe. Ein Turmopfer lenkt ihn weiter, sodass die Dame mattsetzen kann.',
    '037fO':'Die Dame hält den König mit einer Schachfolge fest. In der Beispielvariante werden beide dazwischengestellten Verteidiger nacheinander geschlagen; der letzte Schlag setzt matt.',
    '0212b':'Der Läuferschlag eröffnet den Mattangriff. Die Dame folgt mit Schach und dringt anschließend zum Matt auf die Grundreihe ein.',
    '02pbx':'Die Dame zwingt den König in die Ecke. Ihr anschließendes Opfer lenkt den verteidigenden Turm ab, sodass der angreifende Turm mattsetzt.',
    '01oma':'Turm- und Damenopfer lenken die Verteidiger auf die Grundreihe. Der Springer setzt dann ein ersticktes Matt: Die eigenen Figuren nehmen dem gegnerischen König seine Fluchtfelder.',
}

PIECE_NAMES={1:'Bauer',2:'Springer',3:'Läufer',4:'Turm',5:'Dame',6:'König'}
PIECE_VALUES={1:100,2:320,3:330,4:500,5:900,6:0}


def material_balance(board,color):
    return sum(PIECE_VALUES[p.piece_type]*(1 if p.color==color else -1) for p in board.piece_map().values())


SAN_GERMAN = str.maketrans("KQRBN", "KDTLS")


def score_text(cp):
    return f"{cp/100:+.2f}".replace(".", ",")


def san(board, move):
    return board.san(move).translate(SAN_GERMAN)


def captured_piece(board, move):
    if board.is_en_passant(move):
        return chess.PAWN
    return board.piece_type_at(move.to_square)


def capture_text(piece):
    if piece == chess.QUEEN:
        return "die Dame"
    if piece == chess.PAWN:
        return "einen Bauern"
    return "den " + PIECE_NAMES[piece]


def move_description(board, move):
    piece = board.piece_type_at(move.from_square)
    subject = "Die Dame" if piece == chess.QUEEN else "Der " + PIECE_NAMES[piece]
    target = chess.square_name(move.to_square)
    captured = captured_piece(board, move)
    if board.is_castling(move):
        side = "kurz" if board.is_kingside_castling(move) else "lang"
        return f"Der König rochiert {side}."
    if move.promotion:
        piece_name = PIECE_NAMES[move.promotion]
        promoted = "eine Dame" if move.promotion == chess.QUEEN else "einen " + piece_name
        return f"Der Bauer wandelt sich auf {target} in {promoted} um."
    if board.is_en_passant(move):
        return "Der Bauer schlägt en passant und nimmt den gegnerischen Bauern neben seinem Ausgangsfeld vom Brett."
    if captured:
        return f"{subject} schlägt {capture_text(captured)} auf {target}."
    return f"{subject} zieht nach {target}."


def legal_line(board, variation):
    position = board.copy(stack=False)
    moves = []
    for uci in variation:
        move = chess.Move.from_uci(uci)
        if move not in position.legal_moves:
            break
        moves.append(move)
        position.push(move)
    return moves


def mate_replies(after, moves):
    """Show actual replies and the mate against each, with no engine approximation."""
    answers = list(after.legal_moves)
    if len(moves) > 1 and moves[1] in answers:
        answers.remove(moves[1])
        answers.insert(0, moves[1])
    examples = []
    for reply in answers[:2]:
        reply_san = san(after, reply)
        threatened_piece = after.piece_type_at(reply.to_square)
        takes_attacker = (moves and reply.to_square == moves[0].to_square and after.is_capture(reply))
        after.push(reply)
        try:
            for finish in after.legal_moves:
                finish_san = san(after, finish)
                if finish_san.endswith("#"):
                    if takes_attacker:
                        examples.append(f"Selbst wenn der Gegner mit {reply_san} {capture_text(threatened_piece)} schlägt, setzt {finish_san} matt.")
                    else:
                        examples.append(f"Auf {reply_san} folgt {finish_san}.")
                    break
        finally:
            after.pop()
    return " ".join(examples)


def material_idea(board, moves):
    side = board.turn
    position = board.copy(stack=False)
    pivot = None
    facts = []
    for index, move in enumerate(moves):
        captured = captured_piece(position, move)
        if index == 1 and move.to_square == moves[0].to_square and position.is_capture(move):
            action = "zurückschlagen" if board.is_capture(moves[0]) else f"{capture_text(captured)} schlagen"
            facts.append(f"Der Gegner kann mit {san(position, move)} {action}.")
        if index >= 2 and position.turn == side and captured:
            value = PIECE_VALUES[captured]
            if pivot is None or value > pivot[0]:
                dots = "." if position.turn else "..."
                notation = f"{position.fullmove_number}{dots}{san(position, move)}"
                pivot = (value, notation, captured, chess.square_name(move.to_square))
        position.push(move)
    if pivot:
        _, name, piece, target = pivot
        attacker = "Weiß" if side else "Schwarz"
        facts.append(f"Mit {name} schlägt {attacker} in der Fortsetzung {capture_text(piece)} auf {target}.")
    gain = material_balance(position, side) - material_balance(board, side)
    if gain >= 100:
        amount = f"{gain/100:.1f}".rstrip("0").rstrip(".").replace(".", ",")
        unit = "Bauernwert" if amount == "1" else "Bauernwerte"
        facts.append(f"Die Materialbilanz verbessert sich in dieser Variante um rund {amount} {unit}.")
    return " ".join(facts)


def alternative_idea(board, check):
    runner = legal_line(board, check.get("runner_pv", (check["runner_up_move"],)))
    if not runner:
        return ""
    alternative = san(board, runner[0])
    details = f"Nach {alternative}"
    if len(runner) > 1:
        after = board.copy(stack=False)
        after.push(runner[0])
        reply = san(after, runner[1])
        captured = captured_piece(after, runner[1])
        if captured:
            target = chess.square_name(runner[1].to_square)
            details += f" kann der Gegner mit {reply} {capture_text(captured)} auf {target} schlagen."
        else:
            details += f" antwortet der Gegner in der Engine-Variante mit {reply}."
    else:
        details += " fällt die Bewertung deutlich ab."
    best_score = score_text(check["best"]["cp"])
    alternative_score = score_text(check["runner_up"]["cp"])
    return f"{details} Stockfish bewertet den Lösungszug mit {best_score} und {alternative} mit {alternative_score}, jeweils aus Sicht der Seite am Zug."


def generated_explanation(puzzle):
    board = chess.Board(puzzle.view["fen"])
    move = chess.Move.from_uci(puzzle.best_move)
    if move not in board.legal_moves:
        return "Die Ausgangsstellung wurde verändert."
    after = board.copy(stack=False)
    after.push(move)
    opening = f"{san(board, move)}. {move_description(board, move)}"
    if after.is_checkmate():
        opening += " Der Zug setzt sofort matt. Der gegnerische König hat kein Fluchtfeld und keine legale Abwehr."
    elif after.is_check():
        opening += " Der Gegner muss auf das Schach reagieren."
    if puzzle.chess_record["fen"] != board.fen():
        return opening

    moves = legal_line(board, puzzle.principal_variation[:8])
    paragraphs = [opening]
    if puzzle.view["task"] == "mate":
        count = puzzle.view["mate_in"]
        if count == 2:
            replies = mate_replies(after, moves)
            if replies:
                paragraphs.append(replies)
            paragraphs.append("Nur dieser erste Zug erzwingt Matt im zweiten eigenen Zug gegen jede legale Verteidigung.")
    else:
        idea = material_idea(board, moves)
        if idea:
            paragraphs.append(idea)
        if moves:
            paragraphs.append("Geprüfte Hauptvariante · " + board.variation_san(moves).translate(SAN_GERMAN))
        alternative = alternative_idea(board, puzzle.chess_record["engine_checks"][-1])
        if alternative:
            paragraphs.append(alternative)
    return "\n\n".join(paragraphs)
