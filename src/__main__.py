import argparse
import json
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--functions_definition',
        default='data/input/functions_definition.json'
    )
    parser.add_argument(
        '--input',
        default='data/input/function_calling_tests.json'
    )
    parser.add_argument(
        '--output',
        default='data/output/function_calling_results.json'
    )
    return parser.parse_args()


def main() -> None:
    print("hola")


if __name__ == "__main__":
    try:
        print("CALL ME MAYBE", flush=True)
        args = parse_args()
        print(f"Arguments: {args}", flush=True)
        main()

    except FileNotFoundError as e:
        print(f"File not found: {e.filename}")
        sys.exit(1)
    except PermissionError as e:
        print(f"Permission denied in this file {e.filename}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e.msg}" +
              f"at line {e.lineno} column {e.colno}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error ocurred: {str(e)}")
        sys.exit(1)
