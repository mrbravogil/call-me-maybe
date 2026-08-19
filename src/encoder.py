from pydantic import BaseModel
from typing import Any
import re


WORD_PATTERN = re.compile(r'''
    "(?:\\.|[^"])*"   |
    '(?:\\.|[^'])*'   |
    \S+
''', re.VERBOSE)


class Encoder(BaseModel):
    _trie: dict[str, Any]
    _vocab: list[str | None]

    def __init__(self, tokens: dict[str, int]) -> None:
        """
        ENCODER class constructor. It builds the eNCODER's
        trie and vocab.
        """
        max_token_id = max(tokens.values())
        vocab: list[str | None] = [None] * (max_token_id + 1)
        trie: dict[str, Any] = {}
        print("\nENCODER:")
        print("🛠️ Building...")

        for word, token in tokens.items():
            vocab[token] = word
            node: dict[str, Any] = trie
            for c in word:
                if c not in node:
                    node = node.setdefault(c, {})
            node['token'] = token
        super().__init__()
        self._trie = trie
        self._vocab = vocab
        print("✅Created...")

    def encode(self, text: str) -> list[int]:
        """Translates standard text to a list of token ids for LLM."""
        text = standard_to_llm(text)
        ids: list[int] = []
        i = 0
        while i < len(text):
            node = self._trie
            match_id: int | None = None
            match_len: int = -1
            j = i

            while j < len(text) and text[j] in node:
                node = node[text[j]]
                j += 1
                if 'token' in node:
                    match_id = node['token']
                    match_len = j - i
                if match_id is not None:
                    ids.append(match_id)
                    i += match_len
                else:
                    i += 1

        return ids

    def encode_separated_words(self, text: str) -> list[list[int]]:
        """Returns tokenized prompt fragments."""
        ids: list[list[int]] = []

        colon_match = re.search(r':\s*(.+)$', text)
        if colon_match:
            content = colon_match.group(1).strip()
            ids.append(self.encode(content))

        e_text = text.replace('\\"', '"')
        parts = WORD_PATTERN.findall(e_text)
        for p in parts:
            p.strip('".,!?:;\\')
            p.strip("'")
            if not p:
                continue
            else:
                ids.append(self.encode(p))
        return ids

    def decode(self, tokens: list[int] | int) -> str:
        """Translates LLM tokens to standard text."""
        if isinstance(tokens, int):
            return self._vocab[tokens] or ''
        return llm_to_standard(
            " ".join(self._vocab[token] or '' for token in tokens))


def llm_to_standard(text: str) -> str:
    """
    Replaces special AI characters for space, tab and new line with
    standard language
    """
    return text.replace('Ġ', ' ').replace('Ċ', '\n').replace('ĉ', '\t')


def standard_to_llm(text: str) -> str:
    """
    Replaces standard spaces, tabs and new line chars with special ones
    AI can understand
    """
    return text.replace(' ', 'Ġ').replace('\n', 'Ċ').replace('\t', 'ĉ')
