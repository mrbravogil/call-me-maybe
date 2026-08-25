# Call Me Maybe

Call Me Maybe is a small function-calling prototype that converts natural-language prompts into structured JSON function calls.

The project uses a local small language model (`Qwen3-0.6B`) plus a routing layer that maps user prompts to a predefined function schema and emits the selected function name with arguments.

## What the project does

- Loads a local Hugging Face model through `llm_sdk`
- Reads a JSON file with available function definitions
- Processes a list of prompts from an input file
- Produces JSON function-call outputs in `data/output/`

## Project structure

| Path | Purpose |
| --- | --- |
| `src/__main__.py` | CLI entrypoint used by `make run` |
| `src/call_me_maybe.py` | Prompt processing and function-call assembly |
| `src/llm.py` | LLM wrapper and routing/token selection logic |
| `src/encoder.py` | Custom token encoding helpers |
| `llm_sdk/` | Local SDK that loads the Hugging Face model |
| `data/input/` | Function definitions and prompt test cases |
| `data/output/` | Generated function call results |

## Run

```bash
make run
```

This command reads:

- `data/input/functions_definition.json`
- `data/input/function_calling_tests.json`

And writes output to:

- `data/output/function_calls.json`

## Dependencies

```bash
uv sync --no-install-project
```

Or install the main dependencies manually:

```bash
uv add numpy pydantic torch transformers --frozen
uv add --dev flake8 mypy --frozen
uv lock
```

## Issues found

The current implementation has a few important issues that affect runtime and maintainability:

1. **Slow routing path**  
   Function selection in `src/llm.py` is done token by token, and each step triggers a full forward pass of the model.

2. **Repeated full-context inference**  
   The router recomputes logits from the whole prompt context instead of using incremental caching.

3. **CPU-only execution in the current environment**  
   The runtime is currently falling back to CPU, which increases total execution time significantly.

4. **Sequential prompt processing**  
   Prompts are processed one by one in `src/__main__.py`, with no batching or parallel execution.

5. **Extra startup overhead**  
   The program loads the tokenizer/model and also builds a custom encoder from vocab files, which adds startup cost.

## Current performance concern

At the moment, `make run` takes around 12 minutes to process the full prompt set. The main optimization target is to reduce total runtime to 5 minutes or less.

## Next improvement directions

- Replace LLM-based function routing with deterministic routing rules for the current small function set
- Or keep LLM routing but add incremental cache / better scoring
- Reduce startup work tied to vocab loading and encoder construction
- Re-evaluate batching once the routing bottleneck is fixed
