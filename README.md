# Call Me Maybe

Call Me Maybe is a small function-calling prototype that turns a natural-language prompt into a structured JSON function call using a local model and a predefined JSON schema.

The current implementation keeps a correctness-first approach: it loads a local small language model through `llm_sdk`, selects the target function from a list of available function names, and then extracts the arguments for that function before returning the final JSON payload.

## Introduction

- Loads the local Hugging Face-backed model through `llm_sdk`
- Reads a JSON file of available function definitions
- Validates JSON inputs and function schemas
- Creates a custom token encoder from the model vocabulary
- Routes the prompt to one target function using constrained token selection
- Generates or infers the function arguments
- Emits a final JSON object shaped like:

```json
{
  "prompt": "What is the sum of 2 and 3?",
  "name": "fn_add_numbers",
  "parameters": {"a": 2, "b": 3}
}
```

## Description

The actual pipeline is:

1. `src/__main__.py` loads the model and builds the encoder.
2. `CallMeMaybe` loads all function definitions from `data/input/functions_definition.json`.
3. `set_instructions()` injects the full function schema into the model context.
4. `LLM.next_option()` chooses the function name by decoding token sequences under a legal-token mask.
5. Once a function is selected, the app switches to a function-specific instruction set.
6. `_generate_arguments_with_llm()` asks the model for a JSON object of arguments.
7. If that fails, `Parser.infer_arguments()` is used as a fallback strategy.
8. `FunctionDefinition.validate_arguments()` normalizes and validates the final values.
9. `FunctionResponse.json_schema()` serializes the final output as JSON.

This is a correctness-oriented path, not a lightweight classifier. The model is still used for routing and argument extraction, but the selection is constrained to valid function names and validated outputs.

## Project structure

| Path | Purpose |
| --- | --- |
| `src/__main__.py` | CLI entrypoint and orchestration loop |
| `src/call_me_maybe.py` | Main prompt routing, argument extraction, output assembly |
| `src/llm.py` | Local model wrapper and masked token selection |
| `src/parser.py` | Rule-based fallback argument inference |
| `src/function.py` | Function schema validation and response typing |
| `src/encoder.py` | Custom token encoder/decoder helpers |
| `llm_sdk/` | Local SDK that loads the model and vocabulary |
| `data/input/` | Function definitions and prompt datasets |
| `data/output/` | Generated JSON outputs |

## Important

- The app prioritizes correctness over speed.
- Routing is performed by repeated token-level model calls through `next_token()` and `next_option()`.
- The function list is dynamic: it is built directly from `functions_definition.json`.
- The output is always a JSON object with `prompt`, `name`, and `parameters`.

## How to run it

Install dependencies:

```bash
uv sync --no-install-project
```

Run the default pipeline:

```bash
make run
```

This reads:

- `data/input/functions_definition.json`
- `data/input/function_calling_tests.json`

And writes the result to:

- `data/output/function_calls.json`

There is also a validation/test entrypoint:

```bash
make test
```

## Performance status

This project is operating in the slower but reliable mode:

- function-name routing is done token by token
- the model is queried repeatedly for constrained token decisions
- total runtime on CPU is still noticeable, usually around a few minutes for a small set of prompts

This is a known tradeoff: correctness is preferred over raw throughput.

## Function schema in use

The current example function set includes:

- `fn_add_numbers`
- `fn_greet`
- `fn_reverse_string`
- `fn_get_square_root`
- `fn_substitute_string_with_regex`

The actual schema is defined in `data/input/functions_definition.json` and is loaded at runtime, so the available function list is not hard-coded in the Python logic alone.

## Example output

```json
{"prompt": "What is the sum of 2 and 3?", "name": "fn_add_numbers", "parameters": {"a": 2, "b": 3}}
```

## Current limitations

- Prompts are processed one by one in sequence.
- Startup still includes model vocabulary loading and custom encoder initialization.
- The routing strategy is intentionally conservative and correctness-first.
- The application expects the selected function to be present in the loaded schema.

## Quick maintenance notes

If you edit the function schema or the prompt dataset, the app will automatically pick up the new definitions from the JSON files without requiring code changes to the function registry itself.

The most relevant files to inspect for behavior changes are:

- `src/call_me_maybe.py`
- `src/llm.py`
- `src/function.py`
- `src/parser.py`
