"""Command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from .rebuild import rebuild


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild the Taipei pan-blue presidential-vote analysis."
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="redownload public source files instead of using data/raw cache",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root receiving data/derived and charts",
    )
    args = parser.parse_args()
    rebuild(args.root.resolve(), refresh=args.refresh)


if __name__ == "__main__":
    main()
