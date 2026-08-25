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
    parser.add_argument(
        "--preview-overlay",
        action="store_true",
        help="Open the overlay with sample copy. No mic. No Whisper.",
    )
    args = parser.parse_args(argv)
    if args.preview_overlay:
        from saltvoice_local.preview import run as preview_run

        return preview_run()
    from saltvoice_local.app import run

    return run(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
