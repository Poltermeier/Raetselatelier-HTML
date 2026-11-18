"""Rebuild the browser archive from the tracked Python sources."""
from io import BytesIO
from pathlib import Path
import tarfile
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

root = Path(__file__).resolve().parent.parent
output = BytesIO()


def write(archive, name, content):
    entry = ZipInfo(name, (2020, 1, 1, 0, 0, 0))
    archive.writestr(entry, content, compress_type=ZIP_DEFLATED, compresslevel=9)


with ZipFile(output, "w") as archive:
    for path in sorted((root / "raetselkalender").rglob("*")):
        if path.is_file() and path.suffix in {".py", ".json", ".png"}:
            write(archive, path.relative_to(root).as_posix(), path.read_bytes())
    for name in ("app.py", "chess_adapter.py", "tkinter.py"):
        write(archive, name, (root / "browser" / name).read_bytes())
    with tarfile.open(root / "third_party" / "chess-1.11.2.tar.gz") as source:
        for member in sorted(source.getmembers(), key=lambda member: member.name):
            name = member.name.removeprefix("chess-1.11.2/")
            if member.isfile() and name.startswith("chess/") and name.endswith(".py"):
                write(archive, name, source.extractfile(member).read())

(root / "runtime" / "atelier.zip").write_bytes(output.getvalue())
