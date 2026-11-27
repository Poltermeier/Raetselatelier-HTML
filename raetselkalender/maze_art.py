"""Original layered markers drawn at the scale of a maze tile."""

HERO = ("#204d40", "#459477")
MINOTAUR = ("#6a2929", "#bc563e")
MIRROR = (("#214c70", "#438fb6"), ("#673d82", "#9c63b7"))


def draw_maze_token(canvas, x, y, piece, index):
    tag = ("maze-piece", f"maze-piece:{index}")

    def polygon(points, fill):
        coords = [coordinate for dx, dy in points for coordinate in (x + dx, y + dy)]
        canvas.create_polygon(*coords, fill=fill, tags=tag)

    def oval(left, top, right, bottom, fill, **options):
        canvas.create_oval(x + left, y + top, x + right, y + bottom, fill=fill, tags=tag, **options)

    if piece == "mino":
        rim, face = MINOTAUR
    elif piece == "hero":
        rim, face = HERO
    else:
        rim, face = MIRROR[index]
    oval(-17, -17, 17, 17, rim, outline="#fff9eb", width=1.5)
    oval(-14, -14, 14, 14, face, outline="#f5e3bd", width=1)
    if piece == "hero":
        polygon(((-12, 11), (-8, 5), (-9, -3), (-6, -10), (0, -12), (6, -10),
                 (9, -3), (8, 5), (12, 11)), "#183e35")
        polygon(((-8, -2), (-6, -7), (0, -10), (5, -8), (7, -3), (0, -5)), "#80be92")
        polygon(((-5, -2), (0, -5), (5, -2), (5, 3), (2, 6), (-2, 6), (-5, 3)), "#f4ce98")
        polygon(((-11, 11), (-8, 6), (0, 9), (8, 6), (11, 11)), "#317c62")
        oval(-2, 8, 2, 12, "#ffd575")
    elif piece == "mino":
        polygon(((-5, -6), (-9, -7), (-13, -12), (-13, -7), (-11, -3), (-6, -2)), "#fff0cd")
        polygon(((5, -6), (9, -7), (13, -12), (13, -7), (11, -3), (6, -2)), "#fff0cd")
        polygon(((-6, -8), (6, -8), (10, -3), (8, 6), (4, 11), (-4, 11), (-8, 6), (-10, -3)),
                "#532527")
        polygon(((-8, -3), (0, -7), (8, -3), (6, 0), (0, -2), (-6, 0)), "#d88652")
        oval(-5, 4, 5, 9, "#e5a66b")
        oval(-4, 0, -2, 2, "#ffda84")
        oval(2, 0, 4, 2, "#ffda84")
    else:
        light = ("#87d6ee", "#e9acf6")[index]
        polygon(((0, -13), (10, -6), (10, 6), (0, 13), (-10, 6), (-10, -6)), rim)
        polygon(((0, -12), (9, -6), (0, -1), (-9, -6)), light)
        polygon(((-9, -5), (0, 0), (0, 12), (-9, 6)), face)
        canvas.create_text(x, y + 2, text=str(index + 1), fill="#fffef9", font=("Helvetica", 9, "bold"), tags=tag)
