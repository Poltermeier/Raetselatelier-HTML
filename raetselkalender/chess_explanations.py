"""Factual explanations generated from moves and engine PVs; legacy audit texts."""

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


def score_text(cp):return f'{cp/100:+.2f}'.replace('.',',')


def generated_explanation(puzzle):
    import chess
    board=chess.Board(puzzle.view['fen']);move=chess.Move.from_uci(puzzle.best_move)
    if move not in board.legal_moves:return 'Die Ausgangsstellung wurde verändert.'
    side=board.turn;piece=board.piece_at(move.from_square);name=PIECE_NAMES[piece.piece_type];subject='Die Dame' if piece.piece_type==chess.QUEEN else 'Der '+name
    san=board.san(move);target=chess.square_name(move.to_square);captured=board.piece_at(move.to_square)
    if board.is_castling(move):action='Die '+('kurze' if board.is_kingside_castling(move) else 'lange')+' Rochade bringt König und Turm in ihre neue Stellung.'
    elif move.promotion:
        promoted=PIECE_NAMES[move.promotion];action=f'Der Bauer wandelt sich auf {target} in '+('eine Dame' if move.promotion==chess.QUEEN else 'einen '+promoted)+' um.'
    elif board.is_en_passant(move):action='Der Bauer schlägt einen gegnerischen Bauern en passant.'
    elif captured:
        object_name='die Dame' if captured.piece_type==chess.QUEEN else 'den Bauern' if captured.piece_type==chess.PAWN else 'den '+PIECE_NAMES[captured.piece_type]
        action=f'{subject} schlägt {object_name} auf {target}.'
    else:action=f'{subject} zieht nach {target}.'
    after=board.copy();after.push(move);facts=[f'{san}: {action}']
    if after.is_checkmate():facts.append('Der Zug setzt sofort matt.')
    elif after.is_check():facts.append('Das Schach erzwingt eine Antwort.')
    attacked=[(square,p) for square in after.attacks(move.to_square) if (p:=after.piece_at(square)) is not None and p.color!=side and p.piece_type!=chess.PAWN]
    attacked.sort(key=lambda item:(10000 if item[1].piece_type==chess.KING else PIECE_VALUES[item[1].piece_type]),reverse=True)
    fork=len(attacked)>=2
    if fork:
        names=[PIECE_NAMES[p.piece_type]+' auf '+chess.square_name(square) for square,p in attacked[:2]]
        facts.append('Von dort werden gleichzeitig '+names[0]+' und '+names[1]+' angegriffen.')
    # Artificial UI test positions or subsequently edited records cannot borrow
    # an unrelated engine explanation from the original position.
    if puzzle.chess_record['fen']!=board.fen():return ' '.join(facts)
    if puzzle.view['task']=='mate':
        count=puzzle.view['mate_in'];facts.append(f'Nur dieser erste Zug erzwingt Matt in höchstens {count} '+('eigenem Zug' if count==1 else 'eigenen Zügen')+' gegen jede legale Verteidigung.')
    variation=board.copy();moves=[]
    for uci in puzzle.principal_variation[:8]:
        candidate=chess.Move.from_uci(uci)
        if candidate not in variation.legal_moves:break
        moves.append(candidate);variation.push(candidate)
    if puzzle.view['task']=='best':
        gain=material_balance(variation,side)-material_balance(board,side)
        if gain>=100 and not fork:facts.append(f'In der Beispielvariante verbessert sich die Materialbilanz um etwa {str(round(gain/100,2)).replace(".",",")} Bauerneinheiten.')
        last=puzzle.chess_record['engine_checks'][-1];runner=chess.Move.from_uci(last['runner_up_move'])
        facts.append(f'Stockfish: {score_text(last["best"]["cp"])} statt {score_text(last["runner_up"]["cp"])} bei {board.san(runner)} aus Sicht von '+('Weiß.' if side else 'Schwarz.'))
    if moves:facts.append('Beispiel: '+board.variation_san(moves))
    return ' '.join(facts)
