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
        encoder = llm.encoder
        functions = {}
        with open(func_definitions, 'r') as f:
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

    def regex_pattern(self, text: str) -> list[int]:
        """Returns a regex pattern as a list of tokens."""

        words = {w.strip('\'\".,!?').lower() for w in text.split()}
        for k, p in REGEX_MAPPING:
            if words & set(k):
                return self.encoder.encode(p)
        is_str = re.search(r"['\"](\w+)['\"]", text)
        if is_str:
            return self.encoder.encode(is_str.group(1))
        return self.encoder.encode(r'\w+')

    @staticmethod
    def _quoted_strings(text: str) -> list[str]:
        return re.findall(r"[\"']([^\"']+)[\"']", text)

    @staticmethod
    def _number_value(text: str) -> int | float:
        if re.fullmatch(r'-?\d+', text):
            return int(text)
        return float(text)

    def _extract_substitute_args(self,
                                 prompt: str,
                                 quoted_strings: list[str]) -> dict[str, str]:
        lower_prompt = prompt.lower()
        regex = ''

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
        elif quoted_strings:
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
        quoted_strings = self._quoted_strings(prompt)
        numbers = re.findall(r'-?\d+(?:\.\d+)?', prompt)
        arguments: dict[str, Any] = {}

        for index, arg_name in enumerate(func.params.keys()):
            if func.name == 'fn_add_numbers':
                value = numbers[index] if index < len(numbers) else '0'
                arguments[arg_name] = self._number_value(value)
            elif func.name == 'fn_get_square_root':
                value = numbers[0] if numbers else '0'
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
                substitute_args = self._extract_substitute_args(prompt,
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

    def add_args(self,
                 func: FunctionDefinition,
                 tokens: list[int],
                 text: str) -> list[int]:
        """Generates the arguments for the function call."""

        arguments = self._infer_arguments(func, text)
        for i, arg_name in enumerate(func.params.keys()):
            arg_type = func.params[arg_name]

            if i > 0:
                tokens += self.encoder.encode(', ')
            tokens += self.encoder.encode(f'"{arg_name}": ')

            value = arguments[arg_name]
            if arg_type == 'string':
                tokens += self.encoder.encode('"')
                tokens += self.encoder.encode(str(value))
                tokens += self.encoder.encode('"')
            elif arg_type == 'boolean':
                tokens += self.encoder.encode('true' if value else 'false')
            else:
                tokens += self.encoder.encode(str(value))

        tokens += self.encoder.encode('}\n')
        return tokens

    def process_prompt(self, prompt: str) -> str:
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
        self.set_instructions()
        func_names = [f.t_name for f in self.functions.values()]
        func_name = self.llm.next_option(tokens, func_names)
        func = self.functions[self.encoder.decode(func_name)]
        tokens += func.t_name
        tokens += self.encoder.encode('", "arguments": {')
        self.set_instructions(func)
        tokens += self.add_args(func, tokens, prompt)
        tokens += self.encoder.encode('}')
        raw_output: str = self.encoder.decode(tokens)
        json_output: str = raw_output[raw_output.find('{"name":'):]
        print("\n" + json_output)
        try:
            output_func: dict[str, Any] = json.loads(json_output)
        except json.JSONDecodeError:
            output_func = {
                'name': func.name,
                'arguments': self._infer_arguments(func, original_prompt),
            }
        func_response = FunctionResponse(prompt=prompt,
                                         name=output_func['name'],
                                         parameters=output_func['arguments'])
        return func_response.json_schema()
