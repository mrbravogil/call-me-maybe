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

## Performance work completed

The main bottleneck investigation focused on `src/call_me_maybe.py`, especially inside `process_prompt()` when selecting the target function.

### Original bottleneck

The original routing flow was:

1. Build the user prompt context
2. Call `self.llm.next_option(...)`
3. Let `src/llm.py` choose the function name token by token through `next_token()`
4. Call `get_logits()` for each token step
5. Let `llm_sdk` run a model forward pass for every step

This was expensive because function names can be long, for example `fn_substitute_string_with_regex`, and every token decision required another inference call. In the current CPU-only environment, that pushed `make run` to around **12 minutes**.

## What was tried

During the investigation, the routing layer was temporarily redesigned to reduce runtime:

- dynamic labels were generated from `data/input/functions_definition.json`
- the LLM was asked to classify a short label instead of generating the full function name
- debug timings were added to `src/__main__.py`
- extra tracing was added to `next_token()` and `get_logits()` to understand when the SDK was called and what it received

This helped clarify the runtime behaviour and showed exactly where the cost was concentrated.

## Why that version was not kept

Although the dynamic classification approach reduced runtime significantly, it did not produce reliable routing decisions. In practice, the model kept collapsing to incorrect function choices, especially around the routing step.

That means the faster variant was useful for diagnosis, but not good enough for correct output.

## Current decision

For now, the project continues using the original routing path based on:

- `process_prompt()`
- `next_option()`
- `next_token()`

This path is slower, but it is currently the one producing the correct responses more consistently.

## Current status

- **Correctness priority:** kept
- **Current runtime:** about **8 minutes**
- **Main bottleneck still active:** function-name routing through repeated token-level inference

The work so far reduced the original runtime from roughly **12 minutes** to around **8 minutes**, but the routing stage is still the dominant cost.

## Remaining optimization target

The next optimization goal is to improve routing without losing correctness.

The open problem is not whether `llm_sdk` should be used — it must remain part of the project — but how to use it in a way that is both:

1. dynamic with respect to `functions_definition.json`
2. reliable enough to keep correct function selection
3. faster than the current token-by-token `next_option()` path

## Remaining considerations

1. **CPU-only execution**  
   The runtime is currently falling back to CPU, which still limits inference speed.

2. **Sequential prompt processing**  
   Prompts are processed one by one in `src/__main__.py`.

3. **Startup overhead**  
   The program still loads the tokenizer/model and builds a custom encoder from vocab files.

4. **Future routing refinement**  
   The best future improvement is a routing strategy that stays dynamic, keeps `llm_sdk` in the loop, and avoids the heavy cost of generating long function names token by token.
