import json
import re

from pydantic import BaseModel

from src.encoder import Encoder
from src.function import FunctionDefinition
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
    t_instructions_sufix: list[int]

    def set_instructions(self, func: FunctionDefinition | None = None) -> None:
        """Updates the LLM context with function definitions."""
        definitions: list[int] = []
        if func is not None:
            definitions = func._t_definition
        else:
            definitions = self.t_definitions
        instructions: list[int] = []
        instructions.extend(self.t_instructions_prefix + definitions)
        instructions.extend(self.t_instructions_sufix)
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
        for i, arg_name in enumerate(func._params.keys()):
            arg_type = func._params[arg_name]

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
