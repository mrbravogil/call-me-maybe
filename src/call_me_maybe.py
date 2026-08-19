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

    def add_args(self,
                 func: FunctionDefinition,
                 tokens: list[int],
                 text: str) -> list[int]:
        """Generates the arguments for the function call."""

        mask_options: list[list[int]] = []
        for i, arg_name in enumerate(func.params.keys()):
            arg_type = func.params[arg_name]

            if i > 0:
                tokens += self.encoder.encode(', ')
            tokens += self.encoder.encode(f'"{arg_name}": ')

            if arg_type != 'boolean':
                mask_options.append(self.encoder.encode(text))
            else:
                mask_options.append(self.encoder.encode('true'))
                mask_options.append(self.encoder.encode('false'))

            if arg_type == 'string':
                tokens += self.encoder.encode('"')

            next_option = self.llm.next_option(tokens, mask_options)
            if arg_type == 'int' or arg_type == 'float':
                param = self.encoder.decode(next_option)
                if param.isdigit():
                    next_option += self.encoder.encode('.0')
            tokens += next_option
            if arg_type == 'string':
                tokens += self.encoder.encode('"')

        tokens += self.encoder.encode('}\n')
        return tokens

    def process_prompt(self, prompt: str) -> str:
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
        output_func: dict[str, Any] = json.loads(json_output)
        func_response = FunctionResponse(prompt=prompt,
                                         name=output_func['name'],
                                         parameters=output_func['arguments'])
        return func_response.json_schema()
