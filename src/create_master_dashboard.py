import argparse
from pathlib import Path

from src.master_dashboard import create_master_dashboard


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser():
    parser = argparse.ArgumentParser(
        description="Create the single-file BLACK DOVES master dashboard"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "black_doves_complete_analysis.html",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        result = create_master_dashboard(args.project_root, args.output)
    except (FileNotFoundError, TypeError, ValueError) as error:
        print(f"Master dashboard failed: {error}")
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
