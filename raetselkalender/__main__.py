import argparse
import json

from .catalog import BY_ID, CATALOG, generate
from .hearts import HEARTS_LEVELS


def main():
    parser = argparse.ArgumentParser(description="Simon's Rätselatelier – lokale Python-Anwendung")
    parser.add_argument("--list", action="store_true", help="Katalog und Verfügbarkeit anzeigen")
    parser.add_argument("--headless", action="store_true", help="Rätsel als JSON auf stdout ausgeben")
    parser.add_argument("--type", default="random", choices=["random"] + list(BY_ID))
    parser.add_argument("--seed", type=int, help="Zufalls-Seed für nachvollziehbare Generierung")
    parser.add_argument("--difficulty", choices=HEARTS_LEVELS, default="schwer")
    parser.add_argument('--size',type=int,help='Feldgröße: Katzensuche 4–10; Pipes 4, 5, 7, 10, 12, 15 oder 20')
    parser.add_argument("--show-solution", action="store_true", help="Lösung im JSON mitspeichern")
    parser.add_argument('--diagnose-idle', metavar='DATEI', help='Nach der Rätselerstellung eine lokale CPU-Diagnose als JSON speichern')
    args = parser.parse_args()
    if args.type != "hearts" and args.difficulty not in ("mittel", "schwer"):
        parser.error("Leicht und Experte stehen für Hearts zur Verfügung.")
    if args.size is not None:
        from .pipes import PIPE_SIZES
        if not (args.type in ('katzensuche','katzenraetsel') and 4<=args.size<=10 or args.type=='pipes' and args.size in PIPE_SIZES):
            parser.error('--size: Katzensuche 4–10; Pipes 4, 5, 7, 10, 12, 15 oder 20')
    if args.diagnose_idle and (args.headless or args.list):
        parser.error('--diagnose-idle benötigt die grafische Oberfläche')
    if args.list:
        for item in CATALOG:
            print(f"{item.id:27} {item.availability_label:12} {item.title}")
        return
    if args.headless:
        try:
            puzzle = generate(args.type, args.seed, args.difficulty, size=args.size)
        except (RuntimeError, ValueError) as exc:
            parser.exit(1, f"Generierung fehlgeschlagen: {exc}\n")
        print(json.dumps(puzzle.export(args.show_solution), ensure_ascii=False, indent=2))
        return
    try:
        from .gui import run
        options={('pipe_size' if args.type=='pipes' else 'cat_size'):args.size} if args.size is not None else {}
        run(args.type, args.seed, args.difficulty, diagnose_idle=args.diagnose_idle,**options)
    except ImportError as exc:
        parser.exit(1, f"Grafische Oberfläche nicht verfügbar: {exc}. Installiere Python mit Tk-Unterstützung.\n")


if __name__ == "__main__":
    main()
