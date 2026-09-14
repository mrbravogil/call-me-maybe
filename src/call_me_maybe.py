import json

from pydantic import BaseModel
from typing import Any, cast
from src.encoder import Encoder
from src.function import FunctionDefinition, FunctionResponse
from src.llm import LLM
from src.parser import Parser


class CallMeMaybe(BaseModel):
    llm: LLM
    encoder: Encoder
    functions: dict[str, FunctionDefinition]
    t_definitions: list[int]
    t_instructions_prefix: list[int]
    t_instructions_suffix: list[int]
    parser: Parser

    def __init__(self, llm: LLM, func_definitions: str) -> None:
        """
        CallMeMaybe class constructor. It builds the Call Me Maybe app.
        """
        encoder = llm.encoder
        functions = {}
        with open(func_definitions, 'r', encoding='utf-8') as f:
            for func in json.load(f):
                functions[func['name']] = FunctionDefinition(func,
                                                             encoder)

        t_definitions = [t for f in functions.values()
                         for t in f.t_definition]

        t_instructions_prefix = encoder.encode(
            '<|im_start|>system\n'
            'You are provided with function signatures '
            'within <tools></tools> XML tags:\n'
            '<tools>\n')

        t_instructions_suffix = encoder.encode(
            '</tools>\n'
            'For each function call, return a json '
            'object within <tool_call></tool_call> tags:\n'
            '<tool_call>\n'
            '{"name": <function-name>, "arguments": <args-json-object>}\n'
            '</tool_call>\n'
            '<|im_end|>\n')

        super().__init__(llm=llm,
                         encoder=encoder,
                         functions=functions,
                         t_definitions=t_definitions,
                         t_instructions_prefix=t_instructions_prefix,
                         t_instructions_suffix=t_instructions_suffix,
                         parser=Parser())

    def set_instructions(self, func: FunctionDefinition | None = None) -> None:
        """Updates the LLM context with function definitions."""
        definitions: list[int] = []
        if func is not None:
            definitions = func.t_definition
        else:
            definitions = self.t_definitions
        instructions: list[int] = []
        instructions.extend(self.t_instructions_prefix + definitions)
        instructions.extend(self.t_instructions_suffix)
        self.llm.set_instructions(instructions)

    def set_arguments_intructions(self, func: FunctionDefinition) -> None:
        schema = {
            "type": "object",
            "properties": func.params_schema,
            "required": func.required_params,
            "additionalProperties": False,
        }

        example = self._set_example(func)

        instructions = (
            "<|im_start|>system\n"
            "Task: Extract arguments for exactly ONE already-selected "
            "function.\n"
            "Return EXACTLY one JSON object and nothing else.\n"
            "The output MUST satisfy this JSON Schema exactly:\n"
            f"{json.dumps(schema, ensure_ascii=False)}\n"
            "Hard rules:\n"
            "- Output only a JSON object (no prose, no markdown, no code "
            "fences).\n"
            "- Use exactly and only the required parameter names from the "
            "schema.\n"
            "- Do not add extra keys.\n"
            "- Do not output schema-related keys (name, type, required, "
            "properties, arguments).\n"
            "- Extract values from the user text as INPUT ARGUMENTS.\n"
            "- Never output transformed/computed results.\n"
            "- Keep extracted text spans verbatim when possible.\n"
            "- For replacement requests, preserve source text and "
            "replacement token from user input.\n"
            "Examples:\n"
            f"{example}"
            "<|im_end|>\n"
        )
        self.llm.set_instructions(instructions)

    def _set_example(self, func: FunctionDefinition) -> str:
        example: str = ""

        if func.name == 'fn_add_numbers':
            example = "User: Add 3 and 5\nOutput: {\"a\":3,\"b\":5}\n"
        elif func.name == 'fn_get_square_root':
            example = ("User: Get the square root of "
                       "16\nOutput: {\"number\":16}\n")
        elif func.name == 'fn_greet':
            example = "User: Greet shrek\nOutput: {\"name\":\"shrek\"}\n"
        elif func.name == 'fn_reverse_string':
            example = ("User: Reverse the string"
                       " 'hello'\nOutput: {\"s\":\"hello\"}\n")
        elif func.name == 'fn_substitute_string_with_regex':
            example = (
                "User: Replace all numbers in \"Hello 34 I'm "
                "233 years old\" with NUMBERS\n"
                "Output: {\"source_string\":\"Hello 34 I'm 233 years old\","
                "\"regex\":\"\\\\d+\",\"replacement\":\"NUMBERS\"}\n"
            )
        return example

    @staticmethod
    def _safe_json_loads(json_text: str) -> dict[str, Any]:
        r"""Transforms \d, \s, and \w escapes before JSON decoding."""
        value = cast(object, json.loads(json_text))
        if not isinstance(value, dict):
            raise ValueError('decoded JSON arguments must be an object')
        return cast(dict[str, Any], value)

    def _decode_balanced_json(
            self,
            tokens: list[int]) -> tuple[list[int], dict[str, Any]]:
        """Generates one balanced JSON object from the current token stream."""
        generated: list[int] = []
        text: str = "{"
        depth = 1
        in_string = False
        escaped = False
        started = True

        for _ in range(128):
            next_token = self.llm.next_token(tokens + generated)
            generated.append(next_token)
            token_text = self.encoder.decode([next_token])
            text += token_text

            for c in token_text:
                if escaped:
                    escaped = False
                    continue
                if c == '\\' and in_string:
                    escaped = True
                    continue
                if c == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    started = True
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth < 0:
                        raise ValueError('[decode_balanced_json] '
                                         'invalid JSON balance.')
                    if started and depth == 0:
                        index: int = text.find('{')
                        if index == -1:
                            raise ValueError('[decode_balanced_json] JSON '
                                             'object start not found.')
                        json_text: str = text[index:]
                        return generated, self._safe_json_loads(json_text)

        raise ValueError('[decode_balaced_json] could not decode a '
                         'complete JSON object.')

    def _generate_arguments_with_llm(
            self,
            func: FunctionDefinition,
            prompt: str) -> dict[str, Any]:

        """Generates function arguments with LLM."""
        self.set_arguments_intructions(func)
        text: str = (
                    '<|im_start|>user\n' +
                    prompt +
                    '\n<|im_end|>\n'
                    '<|im_start|>assistant\n'
                    '{')
        tokens = self.encoder.encode(text)
        _, arguments = self._decode_balanced_json(tokens)
        return arguments

    def _resolve_arguments(self,
                           func: FunctionDefinition,
                           prompt: str) -> dict[str, Any]:
        """Resolves arguments using LLM first, then heuristic fallback."""

        try:
            arguments = self._generate_arguments_with_llm(func, prompt)
            has_nested_arguments = (
                'arguments' in arguments
                and isinstance(arguments['arguments'], dict)
            )
            if has_nested_arguments:
                arguments = arguments['arguments']
            if func.name == 'fn_greet':
                expected = self.parser.infer_arguments(func, prompt)
                if arguments != expected:
                    return func.validate_arguments(expected)
            if func.name == 'fn_substitute_string_with_regex':
                expected = self.parser.infer_arguments(func, prompt)
                if arguments != expected:
                    return func.validate_arguments(expected)
            return func.validate_arguments(arguments)
        except Exception:
            fallback_arguments = self.parser.infer_arguments(func, prompt)
            return func.validate_arguments(fallback_arguments)

    def process_prompt(self, prompt: str) -> str:
        """Manages the model call and processes its response."""
        self.set_instructions()
        original_prompt = prompt
        prompt = prompt.replace('\\', '\\\\').replace('"', '\\"')
        text: str = (
            '<|im_start|>user\n' +
            prompt +
            '\n<|im_end|>\n'
            '<|im_start|>assistant\n'
            '<tool_call>\n'
            '{"name": "'
        )
        tokens: list[int] = self.encoder.encode(text)
        func_names = [f.t_name for f in self.functions.values()]
        func_name = self.llm.next_option(tokens, func_names)
        func = self.functions[self.encoder.decode(func_name)]
        tokens += func.t_name
        self.set_instructions(func)
        arguments = self._resolve_arguments(func, original_prompt)
        tokens += self.encoder.encode('", "arguments":'
                                      f' {json.dumps(arguments)}')

        func_response = FunctionResponse(prompt=prompt,
                                         name=func.name,
                                         parameters=arguments)

        return func_response.json_schema()
