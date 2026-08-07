import argparse
import json
import sys
from pydantic import BaseModel, ValidationError
import pathlib
from llm_sdk import Small_LLM_Model  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--functions_definition',
        default='data/input/functions_definition.json'
    )

def main() -> None:
    print("hola")


if __name__ == "__main__":
    try:
        main()

    except FileNotFoundError as e:
        print(f"File not found: {e.filename}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e.msg}" +
              f"at line {e.lineno} column {e.colno}")
    except Exception as e:
        print(f"An unexpected error ocurred: {str(e)}")
