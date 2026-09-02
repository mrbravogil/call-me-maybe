# CallMeMaybe function arguments refactor plan

This document captures the implementation plan and a proposed diff for refactoring `src/call_me_maybe.py` so the model generates function-call arguments instead of building them manually in Python.

## Goal

Move from this flow:

1. Model selects a function name.
2. Python infers arguments with heuristics.
3. Python serializes the arguments by hand.

To this flow:

1. Model selects a function name.
2. Model generates the `arguments` JSON object for that function.
3. Python validates and normalizes the generated arguments.
4. Python falls back to heuristic inference if model generation fails.

---

## Implementation plan

## Phase 1 — Safe refactor in `src/call_me_maybe.py`

### 1. Add an orchestration method

Create:

```python
def _resolve_arguments(
    self,
    func: FunctionDefinition,
    prompt: str,
) -> dict[str, Any]:
```

Responsibilities:

1. Try to generate arguments with the LLM.
2. Validate and normalize the generated payload.
3. Fall back to `_infer_arguments()` if generation fails.

### 2. Add LLM-based argument generation

Create:

```python
def _generate_arguments_with_llm(
    self,
    func: FunctionDefinition,
    prompt: str,
) -> dict[str, Any]:
```

Responsibilities:

- Set instructions for exactly one function.
- Ask the model to return only the JSON object for `arguments`.
- Generate tokens until a full balanced JSON object is produced.
- Parse the output with `json.loads`.

### 3. Add bounded JSON decoding

Create:

```python
def _decode_balanced_json(
    self,
    tokens: list[int],
    max_steps: int = 256,
) -> tuple[list[int], dict[str, Any]]:
```

Responsibilities:

- Start at the first `{`.
- Keep decoding until braces balance.
- Respect quoted strings and escapes.
- Return both the generated tokens and the parsed JSON object.

### 4. Add strict argument validation

Create:

```python
def _validate_arguments(
    self,
    func: FunctionDefinition,
    arguments: dict[str, Any],
) -> dict[str, Any]:
```

Validation rules:

- `arguments` must be a JSON object.
- All required fields must exist.
- No extra fields are allowed.
- Each field must match the expected type.
- Function-specific constraints must be enforced, for example:
  - `fn_get_square_root` must reject negative values.

### 5. Update `process_prompt()`

Replace manual argument construction with:

1. function selection
2. argument resolution through `_resolve_arguments()`
3. final JSON serialization

Conceptual target:

```python
self.set_instructions(func)
arguments = self._resolve_arguments(func, original_prompt)
output_func = {
    "name": func.name,
    "arguments": arguments,
}
```

### 6. Keep heuristics as fallback for now

Do not remove these helpers yet:

- `_infer_arguments()`
- `_extract_regex_args()`
- `_regex_value()`
- `_quoted_strings()`
- `_number_value()`

They remain the safety net while the LLM-based path is stabilized.

---

## Phase 2 — Fix the data model in `src/function.py`

## Problem

`FunctionDefinition.__init__()` currently reduces parameter definitions to simple type strings:

```python
params = {k: v['type'] for k, v in function['parameters'].items()}
```

But the validator later treats parameter values as if they were full schema dictionaries. That is inconsistent.

## Proposed change

Store separate structures:

```python
params: dict[str, str]
params_schema: dict[str, dict[str, Any]]
required_params: list[str]
```

Recommended meaning:

- `params`: quick access to normalized type names
- `params_schema`: original schema per parameter
- `required_params`: exact required argument order/list

## Benefits

- Validation becomes coherent.
- The function schema can be reused directly in prompts.
- Future functions can add richer parameter metadata without rewriting validation logic.

---

## Phase 3 — Improve model instructions

Split the prompting responsibilities into two modes:

1. function selection
2. argument generation for the selected function

The argument-generation instruction should clearly say:

- use only this function
- return only a JSON object
- use exactly the declared parameter names
- respect declared parameter types
- do not add explanations or markdown

---

## Phase 4 — Cleanup

After the new path is stable:

1. remove `add_args()`
2. reduce `_infer_arguments()` to fallback-only status
3. optionally remove old heuristics if they no longer provide value

---

## Recommended implementation order

1. Fix `FunctionDefinition` in `src/function.py`.
2. Add `_validate_arguments()`.
3. Add `_generate_arguments_with_llm()`.
4. Add `_resolve_arguments()` with fallback.
5. Update `process_prompt()`.
6. Test with real prompts.
7. Remove `add_args()` when confidence is high.

---

## Test cases to cover

### `fn_add_numbers`

- `add 4 and 7`
- `sum 3.5 and 2`
- `add -2 and 9`

### `fn_get_square_root`

- `square root of 16`
- `sqrt of 2`
- `square root of -4`

### `fn_greet`

- `greet John`
- `greet "Ana"`

### `fn_reverse_string`

- `reverse "hello world"`

### `fn_substitute_string_with_regex`

- `replace vowels with * in hello`
- `replace "[aeiou]" with "_" in "house"`

### Invalid-generation cases

- incomplete JSON
- wrong type
- missing required field
- extra field

---

## Success criteria

The refactor is successful when:

1. the model still selects the correct function
2. the model generates `arguments`
3. Python validates and normalizes the result
4. fallback works without breaking the app
5. adding a new function requires less ad hoc Python logic

---

## Proposed diff

```diff
diff --git a/src/function.py b/src/function.py
index 1111111..2222222 100644
--- a/src/function.py
+++ b/src/function.py
@@ -1,5 +1,5 @@
 from pydantic import BaseModel, Field, model_validator
-from typing import Any
+from typing import Any
 import json
 from typing_extensions import Self
 from src.encoder import Encoder
@@ -13,9 +13,10 @@ class FunctionDefinition(BaseModel):
     description: str = Field(...)
     t_description: list[int]
-    params: dict[str, Any] = Field(...)
-    t_params: dict[str, list[int]]
+    params: dict[str, str] = Field(...)
+    params_schema: dict[str, dict[str, Any]] = Field(...)
+    required_params: list[str]
     t_definition: list[int]
 
     def __init__(self,
                  function: dict[str, Any],
                  encoder: Encoder):
         name = function['name']
         description = function['description']
-        params = {k: v['type']
-                  for k, v in function['parameters'].items()}
-        t_params = {k: encoder.encode(v['type'])
-                    for k, v in function['parameters'].items()}
+        params_schema = function['parameters']
+        params = {k: v['type'] for k, v in params_schema.items()}
+        required_params = list(params_schema.keys())
 
         t_definition = encoder.encode(json.dumps({
             "name": name,
             "description": description,
             "parameters": {
                 "type": "object",
                 "properties": {
-                    k: {"type": v}
-                    for k, v in params.items()
+                    k: v
+                    for k, v in params_schema.items()
                 },
-                "required": list(params.keys())
+                "required": required_params
             }
         }))
 
@@ -24,9 +25,10 @@ class FunctionDefinition(BaseModel):
                          t_name=encoder.encode(name),
                          description=description,
                          t_description=encoder.encode(description),
                          params=params,
-                         t_params=t_params,
+                         params_schema=params_schema,
+                         required_params=required_params,
                          t_definition=t_definition)
 
     def _json_schema(self) -> str:
         return json.dumps({
@@ -34,10 +36,10 @@ class FunctionDefinition(BaseModel):
             "description": self.description,
             "parameters": {
                 "type": "object",
                 "properties": {
-                    k: {"type": v}
-                    for k, v in self.params.items()
+                    k: v
+                    for k, v in self.params_schema.items()
                 },
-                "required": list(self.params.keys())
+                "required": self.required_params
             }
         })
 
@@ -52,21 +54,15 @@ class FunctionDefinition(BaseModel):
         if not self.params:
             raise ValueError("parameters cannot be empty")
 
-        for name, type in self.params.items():
+        for name, p_type in self.params.items():
             if not name.strip():
                 raise ValueError("parameter name cannot be empty")
-            if not type:
+            if not isinstance(p_type, str) or not p_type:
                 raise ValueError(f"parameter '{name}' cannot be empty")
-            if not isinstance(type, dict):
-                raise ValueError(f"parameter '{name}' must be a dict")
 
-            p_type = type.get("type")
-            if not isinstance(p_type, str):
-                raise ValueError(
-                    f"parameter '{name}' must have a valid str format"
-                )
-            if not p_type:
+            schema = self.params_schema.get(name)
+            if not isinstance(schema, dict):
                 raise ValueError(
-                    f"parameter '{name}' must have a non-empty type"
+                    f"parameter '{name}' must have a valid schema"
                 )
 
         return self
@@ -107,7 +103,7 @@ class FunctionResponse(BaseModel):
     @model_validator(mode="after")
     def validate_add_numbers(self) -> Self:
         if self.name == "fn_add_numbers" or self.name == "fn_get_square_root":
             for param in self.parameters.values():
-                if not isinstance(param, int):
+                if not isinstance(param, (int, float)):
                     raise ValueError("All parameters of fn_add_numbers, "
                                      "fn_get_square_root "
                                      "must be numbers.")
diff --git a/src/call_me_maybe.py b/src/call_me_maybe.py
index 3333333..4444444 100644
--- a/src/call_me_maybe.py
+++ b/src/call_me_maybe.py
@@ -1,5 +1,5 @@
 import json
 import re
-
 from pydantic import BaseModel
 from typing import Any
 from src.encoder import Encoder
@@ -81,6 +81,20 @@ class CallMeMaybe(BaseModel):
         instructions.extend(self.t_instructions_suffix)
         self.llm.set_instructions(instructions)
 
+    def set_argument_instructions(self, func: FunctionDefinition) -> None:
+        """Updates the LLM context to generate arguments for one function."""
+        instruction = (
+            '<|im_start|>system\n'
+            'You are generating arguments for exactly one function.\n'
+            'Return only a valid JSON object for "arguments".\n'
+            'Do not include markdown, explanations, or extra text.\n'
+            'Use exactly the parameter names and types defined below.\n'
+            '<tools>\n'
+        )
+        instruction += self.encoder.decode(func.t_definition)
+        instruction += (
+            '\n</tools>\n<|im_end|>\n'
+        )
+        self.llm.set_instructions(instruction)
+
     @staticmethod
     def _quoted_strings(text: str) -> list[str]:
         """Returns quoted string within the prompt text."""
@@ -156,6 +170,105 @@ class CallMeMaybe(BaseModel):
 
         return arguments
 
+    def _coerce_argument_type(self, arg_type: str, value: Any) -> Any:
+        """Coerces a generated value to the expected function parameter type."""
+        if arg_type == 'string':
+            if isinstance(value, str):
+                return value
+            return str(value)
+
+        if arg_type == 'number':
+            if isinstance(value, (int, float)) and not isinstance(value, bool):
+                return value
+            if isinstance(value, str):
+                return self._number_value(value.strip())
+            raise ValueError(f"cannot coerce {value!r} to number")
+
+        if arg_type == 'integer':
+            if isinstance(value, int) and not isinstance(value, bool):
+                return value
+            if isinstance(value, float) and value.is_integer():
+                return int(value)
+            if isinstance(value, str) and re.fullmatch(r'-?\d+', value.strip()):
+                return int(value.strip())
+            raise ValueError(f"cannot coerce {value!r} to integer")
+
+        if arg_type == 'boolean':
+            if isinstance(value, bool):
+                return value
+            if isinstance(value, str):
+                lowered = value.strip().lower()
+                if lowered == 'true':
+                    return True
+                if lowered == 'false':
+                    return False
+            raise ValueError(f"cannot coerce {value!r} to boolean")
+
+        return value
+
+    def _validate_arguments(
+        self,
+        func: FunctionDefinition,
+        arguments: dict[str, Any],
+    ) -> dict[str, Any]:
+        """Validates and normalizes arguments produced by the LLM."""
+        if not isinstance(arguments, dict):
+            raise ValueError("arguments must be a JSON object")
+
+        extra_keys = set(arguments.keys()) - set(func.required_params)
+        if extra_keys:
+            raise ValueError(f"unexpected arguments: {sorted(extra_keys)}")
+
+        missing_keys = [name for name in func.required_params
+                        if name not in arguments]
+        if missing_keys:
+            raise ValueError(f"missing required arguments: {missing_keys}")
+
+        normalized: dict[str, Any] = {}
+        for arg_name in func.required_params:
+            arg_type = func.params[arg_name]
+            normalized[arg_name] = self._coerce_argument_type(
+                arg_type, arguments[arg_name]
+            )
+
+        if func.name == 'fn_get_square_root':
+            first_value = next(iter(normalized.values()))
+            if first_value < 0:
+                raise ValueError("square root input cannot be negative")
+
+        return normalized
+
+    def _decode_balanced_json(
+        self,
+        tokens: list[int],
+        max_steps: int = 256,
+    ) -> tuple[list[int], dict[str, Any]]:
+        """Generates one balanced JSON object from the current token stream."""
+        generated: list[int] = []
+        text = ""
+        depth = 0
+        in_string = False
+        escaped = False
+        started = False
+
+        for _ in range(max_steps):
+            next_token = self.llm.next_token(tokens + generated)
+            generated.append(next_token)
+            text = self.encoder.decode(generated)
+
+            for ch in self.encoder.decode([next_token]):
+                if escaped:
+                    escaped = False
+                    continue
+                if ch == '\\' and in_string:
+                    escaped = True
+                    continue
+                if ch == '"':
+                    in_string = not in_string
+                    continue
+                if in_string:
+                    continue
+                if ch == '{':
+                    started = True
+                    depth += 1
+                elif ch == '}':
+                    depth -= 1
+                    if started and depth == 0:
+                        return generated, json.loads(text)
+
+        raise ValueError("could not decode a complete JSON object")
+
     def _infer_arguments(
         self,
         func: FunctionDefinition,
@@ -205,33 +318,39 @@ class CallMeMaybe(BaseModel):
 
         return arguments
 
-    def add_args(self,
-                 func: FunctionDefinition,
-                 tokens: list[int],
-                 text: str) -> list[int]:
-        """Generates the arguments for the function call."""
-
-        arguments = self._infer_arguments(func, text)
-        for i, arg_name in enumerate(func.params.keys()):
-            arg_type = func.params[arg_name]
-
-            if i > 0:
-                tokens += self.encoder.encode(', ')
-            tokens += self.encoder.encode(f'"{arg_name}": ')
-
-            value = arguments[arg_name]
-            if arg_type == 'string':
-                tokens += self.encoder.encode('"')
-                tokens += self.encoder.encode(str(value))
-                tokens += self.encoder.encode('"')
-            elif arg_type == 'boolean':
-                tokens += self.encoder.encode('true' if value else 'false')
-            else:
-                tokens += self.encoder.encode(str(value))
-
-        tokens += self.encoder.encode('}\n')
-        return tokens
+    def _generate_arguments_with_llm(
+        self,
+        func: FunctionDefinition,
+        prompt: str,
+    ) -> dict[str, Any]:
+        """Generates function arguments with the LLM."""
+        self.set_argument_instructions(func)
+        text = (
+            '<|im_start|>user\n'
+            f'{prompt}\n'
+            '<|im_end|>\n'
+            '<|im_start|>assistant\n'
+        )
+        tokens = self.encoder.encode(text)
+        _, arguments = self._decode_balanced_json(tokens)
+        return arguments
+
+    def _resolve_arguments(
+        self,
+        func: FunctionDefinition,
+        prompt: str,
+    ) -> dict[str, Any]:
+        """Resolves arguments using LLM first, then heuristic fallback."""
+        try:
+            arguments = self._generate_arguments_with_llm(func, prompt)
+            return self._validate_arguments(func, arguments)
+        except Exception:
+            fallback_arguments = self._infer_arguments(func, prompt)
+            return self._validate_arguments(func, fallback_arguments)
 
     def process_prompt(self, prompt: str) -> str:
         """Manages the model call and processes its response."""
         original_prompt = prompt
         prompt = prompt.replace('\\', '\\\\').replace('"', '\\"')
@@ -249,18 +368,13 @@ class CallMeMaybe(BaseModel):
         func = self.functions[self.encoder.decode(func_name)]
         tokens += func.t_name
-        tokens += self.encoder.encode('", "arguments": {')
-        self.set_instructions(func)
-        tokens += self.add_args(func, tokens, prompt)
-        tokens += self.encoder.encode('}')
-        raw_output: str = self.encoder.decode(tokens)
-        json_output: str = raw_output[raw_output.find('{"name":'):]
-        try:
-            output_func: dict[str, Any] = json.loads(json_output)
-        except json.JSONDecodeError:
-            output_func = {
-                'name': func.name,
-                'arguments': self._infer_arguments(func, original_prompt),
-            }
+        arguments = self._resolve_arguments(func, original_prompt)
+        output_func = {
+            'name': func.name,
+            'arguments': arguments,
+        }
+
+        tokens += self.encoder.encode(
+            f'", "arguments": {json.dumps(arguments)}}}'
+        )
         func_response = FunctionResponse(prompt=prompt,
                                          name=output_func['name'],
                                          parameters=output_func['arguments'])
```

---

## Important notes about the proposed diff

1. The final f-string in `process_prompt()` should be handled carefully because of closing braces. A safer version is:

```python
serialized_arguments = json.dumps(arguments)
tokens += self.encoder.encode('", "arguments": ')
tokens += self.encoder.encode(serialized_arguments)
tokens += self.encoder.encode('}')
```

2. `_decode_balanced_json()` must not count braces naively. Braces inside strings must be ignored.

3. The proposed diff is a working direction, not a guarantee that all edge cases are covered. Validation and tests are still required.
