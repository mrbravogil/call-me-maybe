"""Call Me Maybe: function-calling prototype that converts natural-language
prompts into JSON objects containing a selected function name and its
arguments.

__main__ : This module is the command-line entry point for processing
function-calling prompts.

Usage:
    make run
    make install

Requirements:
    Requirements: Python 3.12 or newer and `uv`.
"""

import argparse
import json
import os
import sys
import time
from pydantic import ValidationError
from dotenv import load_dotenv

from src.encoder import Encoder


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments and return their defaulted values."""
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


def file_validator(inputs: str, definitions: str) -> None:
    with open(inputs, 'r', encoding='utf-8') as c:
        input = json.load(c)
    if not input:
        raise ValueError('JSON input cannot be empty.')
    with open(definitions, 'r', encoding='utf-8') as f:
        functions = json.load(f)
    if not functions:
        raise ValueError('JSON definitions cannot be empty.')


def create_encoder(vocab_path: str) -> Encoder:
    """Build an encoder from the vocabulary stored at ``vocab_path``."""
    with open(vocab_path, 'r', encoding='utf-8') as f:
        tokens = json.load(f)
    return Encoder(tokens)


if __name__ == "__main__":
    try:
        print("\n⚙️ ⚙️ ⚙️ CALL ME MAYBE⚙️ ⚙️ ⚙️", flush=True)
        load_dotenv()
        args = parse_args()
        start = time.time()
        model_load_start = time.time()
        print("Importing dependencies...")
        from llm_sdk.llm_sdk import Small_LLM_Model
        from src.llm import LLM
        from src.call_me_maybe import CallMeMaybe

        file_validator(args.input, args.functions_definition)

        print("\n😃 Calling QWEN 0.6b...")
        small_llm = Small_LLM_Model()
        print("✅QWEN 0.6b...")
        model_load_end = time.time()

        encoder_start = time.time()
        encoder = create_encoder(small_llm.get_path_to_vocab_file())
        encoder_end = time.time()

        wiring_start = time.time()
        llm = LLM(small_llm, encoder)
        cmm = CallMeMaybe(llm, args.functions_definition)
        wiring_end = time.time()

        print(f"⏱️ Model load: {model_load_end - model_load_start:.2f}s")
        print(f"⏱️ Encoder build: {encoder_end - encoder_start:.2f}s")
        print(f"⏱️ App wiring: {wiring_end - wiring_start:.2f}s")

        prompts: list[str] = []
        with open(args.input, 'r', encoding='utf-8') as f:
            prompts = [p['prompt'] for p in json.load(f)]
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        print("\nREQUEST: Processing...")
        processing_start = time.time()
        with open(args.output, 'w', encoding='utf-8') as output:
            output.write("[\n")
            for i, p in enumerate(prompts):
                prompt_start = time.time()
                if len(p.strip()) < 1:
                    raise ValueError(f"Invalid prompt =  '{p}'")
                print(f'\n📓"{p}"...')
                result = cmm.process_prompt(p)
                print(result)
                prompt_end = time.time()
                print(f"⏱️ Prompt time: {prompt_end - prompt_start:.2f}s")
                if i < len(prompts) - 1:
                    output.write(result + ",\n")
                else:
                    output.write(result + "\n")
            output.write("]")
            processing_end = time.time()
            print("⏱️ Prompt processing total: "
                  f"{int((processing_end - processing_start)/60)}s")
        end = time.time()
        print(f"Run: {int((end-start)/60)} minutes")
        print(f"⏱️ Total run: {end - start:.2f}s")
        print(f"Run: {int((end-start)/60)} minutes")

    except FileNotFoundError as e:
        print(f"\nFile not found: {e.filename}")
        sys.exit(1)
    except PermissionError as e:
        print(f"\nPermission denied in this file {e.filename}",
              file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\nError decoding JSON: {e.msg}" +
              f"at line {e.lineno} column {e.colno}")
        sys.exit(1)
    except ValidationError as e:
        print("\nValidation error:")
        print(e.errors())
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error ocurred: {str(e)}")
        sys.exit(1)
    finally:
        print("⚙️ Programme finished...\n")
