import argparse
import json
import os
import sys
import time
from pydantic import ValidationError
from dotenv import load_dotenv

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
                print(f"\n📓'{p}'...")
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
        print(f"File not found: {e.filename}")
        sys.exit(1)
    except PermissionError as e:
        print(f"Permission denied in this file {e.filename}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e.msg}" +
              f"at line {e.lineno} column {e.colno}")
        sys.exit(1)
    except ValidationError as e:
        print("Validation error:")
        print(e.errors())
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error ocurred: {str(e)}")
        sys.exit(1)
    finally:
        print("⚙️ Programme finished...")
