import argparse
import json
import os
import sys
import time

from src.encoder import Encoder


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


def create_encoder(vocab_path: str) -> Encoder:
    with open(vocab_path, 'r') as f:
        tokens = json.load(f)
    return Encoder(tokens)


if __name__ == "__main__":
    try:
        print("\n⚙️ ⚙️ ⚙️ CALL ME MAYBE⚙️ ⚙️ ⚙️", flush=True)
        args = parse_args()
        start = time.time()
        print("Importing dependencies...")
        from llm_sdk.llm_sdk import Small_LLM_Model
        from src.llm import LLM
        from src.call_me_maybe import CallMeMaybe

        print("\n😃 Calling QWEN 0.6b...")
        small_llm = Small_LLM_Model()
        print("✅QWEN 0.6b...")
        encoder = create_encoder(small_llm.get_path_to_vocab_file())
        llm = LLM(small_llm, encoder)
        cmm = CallMeMaybe(llm, args.functions_definition)

        prompts: list[str] = []
        with open(args.input, 'r') as f:
            prompts = [p['prompt'] for p in json.load(f)]
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        print("\nREQUEST: Processing...")
        with open(args.output, 'w') as output:
            output.write("[\n")
            for i, p in enumerate(prompts):
                print(f"📓'{p}'...")
                if i < len(prompts) - 1:
                    output.write(cmm.process_prompt(p) + ",\n")
                else:
                    output.write(cmm.process_prompt(p) + "\n")
            output.write("]")
        end = time.time()
        print(f"Run: {end-start}")

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
    finally:
        print("⚙️ Programme finished...")
