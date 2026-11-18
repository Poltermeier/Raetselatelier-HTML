"""Open the bundled Rätselatelier in a browser, using a loopback-only server."""
from argparse import ArgumentParser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Timer
import webbrowser


class LocalHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".wasm": "application/wasm"}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8750, help="Lokaler Port (Standard: 8750)")
    port = parser.parse_args().port
    directory = Path(__file__).resolve().parent
    handler = partial(LocalHandler, directory=str(directory))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Simon's Rätselatelier: {url}\nZum Beenden Strg+C drücken.", flush=True)
        browser = Timer(0.2, webbrowser.open, args=(url,))
        browser.daemon = True
        browser.start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
