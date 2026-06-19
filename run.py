"""
Crowd Monitor — Production Entry Point

Usage:
    python run.py           # Start with Waitress (production)
    python run.py --dev     # Start with Flask dev server (development)
"""

import argparse
import logging
import os
import platform
import sys
import webbrowser
from threading import Timer


def _open_browser(url: str) -> None:
    Timer(1.5, webbrowser.open_new, args=(url,)).start()


def main() -> None:
    parser = argparse.ArgumentParser(description='Crowd Monitoring System')
    parser.add_argument(
        '--dev',
        action='store_true',
        help='Run in development mode with Flask dev server and hot-reload',
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8090,
        help='Port to listen on (default: 8090)',
    )
    args = parser.parse_args()

    # ── Startup diagnostics ──────────────────────────────────────────────
    print('=' * 60)
    print('  Crowd Monitoring System')
    print('=' * 60)
    print(f'  Python      : {sys.version.split()[0]}')
    print(f'  Platform    : {platform.system()} {platform.release()}')
    print(f'  Mode        : {"Development" if args.dev else "Production (Waitress)"}')
    print(f'  Bind        : {args.host}:{args.port}')
    print('=' * 60)

    # ── Import the Flask app (triggers DB init, model load, etc.) ────────
    from app import app  # noqa: E402

    url = f'http://127.0.0.1:{args.port}/'

    if args.dev:
        # Development: Flask built-in server with debug mode
        print(f'\n  Starting dev server → {url}\n')
        _open_browser(url)
        app.run(host=args.host, port=args.port, debug=True, use_reloader=False)
    else:
        # Production: Waitress WSGI server
        try:
            from waitress import serve
        except ImportError:
            print(
                '\n  ERROR: waitress is not installed.\n'
                '  Install it with:  pip install waitress\n'
                '  Or run in dev mode:  python run.py --dev\n'
            )
            sys.exit(1)

        logger = logging.getLogger('waitress')
        logger.setLevel(logging.INFO)

        print(f'\n  Starting Waitress production server → {url}\n')
        _open_browser(url)
        serve(app, host=args.host, port=args.port, threads=8)


if __name__ == '__main__':
    main()
