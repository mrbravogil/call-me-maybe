"""Heuristics for extracting function arguments from natural-language
prompts.
"""

import re
from pydantic import BaseModel
from typing import Any
from src.function import FunctionDefinition

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


class Parser(BaseModel):
    """Infer typed function arguments from prompt text."""

    def __init__(self) -> None:
        """Initialize the stateless argument parser."""
        super().__init__()

    @staticmethod
    def _quoted_strings(text: str) -> list[str]:
        """Returns quoted string within the prompt text."""
        return re.findall(r"[\"']([^\"']+)[\"']", text)

    @staticmethod
    def _number_value(text: str) -> int | float:
        """Returns numbers within the prompt text."""
        if re.fullmatch(r'-?\d+', text):
            return int(text)
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

    def _extract_regex_args(
        self,
        prompt: str,
        quoted_strings: list[str],
    ) -> dict[str, str]:
        """Extract source text, pattern, and replacement for regex calls."""
        source_match = re.search(
            r"\bin\s+([\"'])(.+?)\1",
            prompt,
            re.IGNORECASE,
        )
        source_string = (
            source_match.group(2)
            if source_match
            else (quoted_strings[-1] if quoted_strings else prompt)
        )

        replacement_match = re.search(
            r"\bwith\s+([\"'])(.+?)\1",
            prompt,
            re.IGNORECASE,
        )
        if replacement_match:
            replacement = replacement_match.group(2)
        else:
            replacement_unquoted = re.search(
                r"\bwith\s+([^\n\r.!?]+)",
                prompt,
                re.IGNORECASE,
            )
            replacement = (
                replacement_unquoted.group(1).strip()
                if replacement_unquoted
                else ""
            )

        regex = self._regex_value(prompt)
        if not regex:
            explicit = re.search(r"/(.+?)/", prompt)
            if explicit:
                regex = explicit.group(1)
            else:
                word = re.search(
                    r"\b(?:word|string)\s+['\"]([^'\"]+)['\"]\s+with\b",
                    prompt,
                    re.IGNORECASE,
                )
                regex = word.group(1) if word else r"\d+"

        return {
            "source_string": source_string,
            "regex": regex,
            "replacement": self.normalize_replacement(replacement)
        }

    @staticmethod
    def normalize_replacement(value: str) -> str:
        """Expand spoken names of common replacement characters."""
        special_characters = {
            'asterisk': '*',
            'asterisks': '*',
            'star': '*',
            'stars': '*',
            'underscore': '_',
            'dash': '-',
            'hyphen': '-',
            'dot': '.',
            'period': '.',
            'space': ' ',
        }
        return special_characters.get(value.strip().lower(), value)

    def infer_arguments(
        self,
        func: FunctionDefinition,
        prompt: str,
    ) -> dict[str, Any]:
        """Infer arguments for ``func`` from the supplied prompt."""

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
