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

## Performance issue found

The main bottleneck was in `src/call_me_maybe.py` during function routing.

Originally, `CallMeMaybe.process_prompt()` delegated function selection to the LLM by asking it to build the function name token by token. That routing path looked roughly like this:

1. Build the prompt context for the user request
2. Call `self.llm.next_option(...)`
3. Let `src/llm.py` select the function name one token at a time
4. For each token step, call `get_logits()`
5. Inside `llm_sdk`, run a full model forward pass to get the next-token logits

This design created a major performance problem:

- the model was used to generate long function names such as `fn_substitute_string_with_regex`
- the selection was greedy and token-by-token
- each token decision triggered a full inference pass
- the whole run executed on CPU in the current environment

As a result, `make run` was taking around **12 minutes** for the current prompt set.

## How the bottleneck was resolved

The routing logic was redesigned inside `CallMeMaybe` to keep the system dynamic while removing the expensive token-by-token function-name generation.

### Previous approach

- Functions were loaded dynamically from `data/input/functions_definition.json`
- The LLM tried to emit the full function name directly
- This made routing expensive and slow

### New dynamic approach

- Functions are still loaded dynamically from `data/input/functions_definition.json`
- `CallMeMaybe` now builds a dynamic list of candidate functions from those definitions
- Instead of generating a long function name token by token, the routing step can classify among short candidate labels
- The rest of the pipeline continues to infer arguments locally and assemble the final JSON response

This preserves the dynamic nature of the project:

- adding new functions to `functions_definition.json` updates the candidate set
- the router is no longer tied to a fully hardcoded fixed list
- the LLM integration remains part of the architecture

## Practical outcome

After removing the heavy token-by-token routing bottleneck in `CallMeMaybe`, total runtime dropped from about **12 minutes** to about **36 seconds** in the current environment.

## Remaining considerations

There are still additional optimization opportunities:

1. **CPU-only execution**  
   The runtime is currently falling back to CPU, which still limits inference speed.

2. **Sequential prompt processing**  
   Prompts are processed one by one in `src/__main__.py`.

3. **Startup overhead**  
   The program still loads the tokenizer/model and builds a custom encoder from vocab files.

4. **Future routing refinement**  
   The ideal long-term design is to use `llm_sdk` for efficient dynamic classification, not for long token-by-token function-name generation.
