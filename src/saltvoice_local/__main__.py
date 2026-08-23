from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="saltvoice-local",
        description="Offline Saltvoice: local Whisper speech-to-text pasted into Grok Bot.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Load the local Whisper model and exit.",
    )
    args = parser.parse_args(argv)
    from saltvoice_local.app import run

    return run(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
