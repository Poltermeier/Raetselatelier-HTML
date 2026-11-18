"""Find a bundled or explicitly installed Stockfish without importing chess."""
import os
from pathlib import Path
import shutil
import sys


def stockfish_path():
    configured=os.environ.get('ATELIER_STOCKFISH')
    if configured:
        path=Path(configured).expanduser()
        return str(path.resolve()) if path.is_file() else None
    filename='stockfish.exe' if os.name=='nt' else 'stockfish'
    candidates=[]
    if getattr(sys,'frozen',False):candidates.append(Path(sys._MEIPASS)/'engine'/filename)
    candidates.extend((Path(__file__).resolve().parents[1]/'.tools'/'stockfish'/filename,
                       Path.cwd()/'.tools'/'stockfish'/filename))
    system=shutil.which(filename)
    if system:candidates.append(Path(system))
    if os.name!='nt':candidates.append(Path('/usr/games/stockfish'))
    return next((str(path.resolve()) for path in candidates if path.is_file()),None)


def stockfish_missing_message():
    return ('Schachrätsel benötigt Stockfish für frisch erzeugte und geprüfte Stellungen. '
            'Im Projektordner einmal ausführen: python tools/install_stockfish.py '
            'Danach das Programm neu starten. Oder den Engine-Pfad mit ATELIER_STOCKFISH angeben. Die Windows-EXE enthält die Engine bereits.')
