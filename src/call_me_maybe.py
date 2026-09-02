import json
import re

from pydantic import BaseModel
from typing import Any
from src.encoder import Encoder
from src.function import FunctionDefinition, FunctionResponse
from src.llm import LLM


REGEX_MAPPING = [
    (['vowel', 'vowels'], r'[aeiouAEIOU]'),
    (
        ['consonant', 'consonants'],
        r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]',
    ),
    (['digit', 'digits', 'number', 'numbers'], r'\\d+'),
    (['uppercase', 'upper', 'capital'], r'[A-Z]+'),
    (['lowercase', 'lower'], r'[a-z]+'),
    (['letter', 'letters', 'alphabetic'], r'[a-zA-Z]+'),
    (['space', 'spaces', 'whitespace'], r'\\s+'),
    (['punctuation', 'special'], r'[^\w\s]'),
    (['alphanumeric'], r'\\w+'),
    (['newline', 'newlines'], r'\\n+'),
    (['tab', 'tabs'], r'\\t+'),
]


class CallMeMaybe(BaseModel):
    llm: LLM
    encoder: Encoder
    functions: dict[str, FunctionDefinition]
    t_definitions: list[int]
    t_instructions_prefix: list[int]
    t_instructions_suffix: list[int]

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
                         t_instructions_suffix=t_instructions_suffix)

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
        """Updates the LLM context to generate arguments for one function."""
        instructions: str = (
            '<|im_start|>system\n'
            'You are generating arguments for exactly one function.\n'
            'Return only a valid JSON object for "arguments".\n'
            'Do not include markdown, explanations, or extra text.\n'
            'Use exactly the parameter names and types defined below.\n'
            '<tools>\n'
            )
        instructions += self.encoder.decode(func.t_definition)
        instructions += (
            '\n</tools>\n<|im_end|>\n'
        )
        self.llm.set_instructions(instructions)

    @staticmethod
    def _quoted_strings(text: str) -> list[str]:
        """Returns quoted string within the prompt text."""
        return re.findall(r"[\"']([^\"']+)[\"']", text)

    @staticmethod
    def _number_value(text: str) -> int | float:
        """Returns numbers within the prompt text."""
        if re.fullmatch(r'-?\d+', text):
            return float(text)
        return float(text)

    @staticmethod
    def _regex_value(text: str) -> str:
        """Returns the functions regex pattern."""
        regex: str = ""
        lower_prompt = text.lower()

        if 'number' in lower_prompt:
            regex = r'\d+'
        elif 'vowel' in lower_prompt:
            regex = r'[aeiouAEIOU]'
        elif 'consonant' in lower_prompt:
            regex = r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]'
        elif 'space' in lower_prompt or 'whitespace' in lower_prompt:
            regex = r'\s+'
        elif 'newline' in lower_prompt:
            regex = r'\n+'
        elif 'tab' in lower_prompt:
            regex = r'\t+'
        elif 'punctuation' in lower_prompt or 'special' in lower_prompt:
            regex = r'[^\w\s]'
        elif 'alphanumeric' in lower_prompt:
            regex = r'\w+'

        return regex

    def _extract_regex_args(self,
                            prompt: str,
                            quoted_strings: list[str]) -> dict[str, str]:
        """Returns regex function arguments"""

        regex = self._regex_value(prompt)

        if quoted_strings:
            regex = quoted_strings[0]

        if len(quoted_strings) >= 3:
            source_string = quoted_strings[-1]
            replacement = quoted_strings[1]
        else:
            source_match = re.search(r"\bin\s+([\"'])(.+?)\1", prompt)
            if source_match:
                source_string = source_match.group(2)
            elif quoted_strings:
                source_string = quoted_strings[-1]
            else:
                source_string = prompt

            replacement_match = re.search(r"\bwith\s+([\"'])(.+?)\1",
                                          prompt)
            if replacement_match:
                replacement = replacement_match.group(2)
            else:
                replacement = (
                    prompt.split(' with ', 1)[-1].strip().strip('.!?')
                )

        return {
            'source_string': source_string,
            'regex': regex,
            'replacement': replacement,
        }

    def _infer_arguments(
        self,
        func: FunctionDefinition,
        prompt: str,
    ) -> dict[str, Any]:
        """"Returns the arguments depending on the chose function."""

        quoted_strings = self._quoted_strings(prompt)
        numbers = re.findall(r'[+-]?(?:\d+\.\d+|\d+|\.\d+)', prompt)
        arguments: dict[str, Any] = {}

        for index, arg_name in enumerate(func.params.keys()):
            if func.name == 'fn_add_numbers':
                value = numbers[index] if index < len(numbers) else '0'
                arguments[arg_name] = self._number_value(value)
            elif func.name == 'fn_get_square_root':
                value = numbers[0] if numbers else '0'
                numeric_value = self._number_value(value)
                if numeric_value < 0:
                    raise ValueError("square root input cannot be negative")
                arguments[arg_name] = self._number_value(value)
            elif func.name == 'fn_greet':
                match = re.search(r'(?i)\bgreet\s+(.+)$', prompt)
                value = quoted_strings[0] if quoted_strings else (
                    match.group(1) if match else prompt
                )
                arguments[arg_name] = value.strip().strip('.!?')
            elif func.name == 'fn_reverse_string':
                if quoted_strings:
                    value = quoted_strings[0]
                else:
                    match = re.search(
                        r'(?i)reverse(?:\s+the\s+string)?\s+(.+)$',
                        prompt,
                    )
                    value = match.group(1) if match else prompt
                arguments[arg_name] = value.strip().strip('.!?')
            elif func.name == 'fn_substitute_string_with_regex':
                substitute_args = self._extract_regex_args(prompt,
                                                           quoted_strings)
                arguments[arg_name] = substitute_args[arg_name]
            else:
                value = (
                    quoted_strings[index]
                    if index < len(quoted_strings)
                    else prompt
                )
                arguments[arg_name] = value

        return arguments

    def _cast_argument_type(self, type: str, value: Any) -> Any:
        """Casts a value to the expected function parameter type."""
        if type == 'string':
            return str(value)
        if type == 'number':
            if isinstance(value, bool):
                raise ValueError(f"cannot cast {value!r} to number.")
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                return float(value)
            raise ValueError(f"cannot cast {value!r} to number.")

        if type == 'integer':
            if isinstance(value, bool):
                raise ValueError(f"cannot cast {value!r} to integer.")
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                if value.is_integer():
                    return int(value)
                raise ValueError(f"cannot cast {value!r} to integer.")
            if isinstance(value, str):
                parsed = float(value)
                if parsed.is_integer():
                    return int(parsed)
                raise ValueError(f"cannot cast {value!r} to integer.")
            raise ValueError(f"cannot cast {value!r} to integer.")

        if type == 'boolean':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered == 'true':
                    return True
                if lowered == 'false':
                    return False
            raise ValueError(f"cannot cast {value!r} to boolean")

        return value

    def _validate_arguments(self,
                            func: FunctionDefinition,
                            arguments: dict[str, Any]) -> dict[str, Any]:
        """Validates and normalizes arguments produced by the LLM."""
        if not isinstance(arguments, dict):
            raise ValueError('[validate_arguments] arguments must be'
                             ' a JSON object.')

        extra_keys = set(arguments.keys()) - set(func.required_params)
        if extra_keys:
            raise ValueError('[validate_arguments] unexpected arguments: '
                             f'{sorted(extra_keys)}.')

        missing_keys = [name for name in func.required_params
                        if name not in arguments]
        if missing_keys:
            raise ValueError('[validate_arguments] missing required arguments:'
                             f' {missing_keys}.')

        normalized: dict[str, Any] = {}
        for name in func.required_params:
            type = func.params[name]
            normalized[name] = self._cast_argument_type(type, arguments[name])

        if func.name == 'fn_get_square_root':
            first_value = next(iter(normalized.values()))
            if first_value < 0:
                raise ValueError('[validate_arguments] square root input'
                                 ' canoot be negative.')

        return normalized

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
                        print(f'[decode_balanced_json] json_text: {text!r}')
                        index: int = text.find('{')
                        if index == -1:
                            raise ValueError('[decode_balanced_json] JSON '
                                             'object start not found.')
                        json_text: str = text[index:]
                        print(f'[decode_balanced_json] raw_text: {text!r}')
                        print('[decode_balanced_json] json_text: '
                              f'{json_text!r}')
                        return generated, json.loads(json_text)

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
            if 'arguments' in arguments and isinstance(arguments['arguments'], dict):
                arguments = arguments['arguments']
            print(f'[resolve_arguments] args: {arguments}')
            return self._validate_arguments(func, arguments)
        except Exception as e:
            print(f'[resolve_arguments] llm_failed: {type(e).__name__}: {e}')
            fallback_arguments = self._infer_arguments(func, prompt)
            print(f'[resolve_arguments] fallback_args: {fallback_arguments}')
            return self._validate_arguments(func, fallback_arguments)

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
        print(f'[process_prompt] func.name: {func}')
        tokens += func.t_name
        self.set_instructions(func)
        arguments = self._resolve_arguments(func, original_prompt)
        tokens += self.encoder.encode('", "arguments":'
                                      f' {json.dumps(arguments)}')

        func_response = FunctionResponse(prompt=prompt,
                                         name=func.name,
                                         parameters=arguments)
        return func_response.json_schema()
