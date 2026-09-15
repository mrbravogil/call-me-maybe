"""Wrapper around the local language model and constrained token decoding."""

import numpy as np
from pydantic import BaseModel, ConfigDict
from src.encoder import Encoder
from llm_sdk.llm_sdk import Small_LLM_Model


class LLM(BaseModel):
    """Expose instruction-aware logits and constrained token selection."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    llm: Small_LLM_Model
    encoder: Encoder
    t_instruction: list[int] | None

    def __init__(self, llm: Small_LLM_Model, encoder: Encoder):
        """Initialize the wrapper with a model and its encoder."""
        print("\nLLM:")
        print("🛠️ Building...")
        super().__init__(
            llm=llm,
            encoder=encoder,
            t_instruction=None)
        print("✅Created...")

    def set_instructions(self, instructions: list[int] | str) -> None:
        """Set the instructions used as context for LLM requests."""
        if isinstance(instructions, str):
            instructions = self.encoder.encode(instructions)
        self.t_instruction = instructions

    def next_token(self,
                   tokens: list[int],
                   mask: set[int] | None = None) -> int:
        """Return the highest-scoring next token, optionally masked."""

        logits = self.get_logits(tokens, mask)
        selected_token = int(np.argmax(logits))
        return selected_token

    def next_option(
        self,
        tokens: list[int],
        mask_options: list[list[int]]
    ) -> list[int]:
        """Return the highest-scoring option from a list of token sequences."""
        if not mask_options:
            raise ValueError("LLM, next_option(): mask_options cannot "
                             "be empty.")

        candidates = [option[:] for option in mask_options]
        best_option: list[int] = []
        current_tokens = tokens[:]

        while True:
            if len(candidates) == 1 and len(best_option) == len(candidates[0]):
                return candidates[0]

            valid_option = [opt for opt in candidates
                            if opt[:len(best_option)] == best_option]
            if not valid_option:
                raise ValueError("LLM, next_option():"
                                 "no valid options remain.")

            last_option = [opt for opt in valid_option
                           if len(opt) == len(best_option)]
            if last_option and len(valid_option) == 1:
                return last_option[0]

            allowed_next_tokens = {
                opt[len(best_option)]
                for opt in valid_option
                if len(opt) > len(best_option)
            }
            if not allowed_next_tokens:
                if last_option:
                    return last_option[0]
                raise ValueError("LLM, next_option(): options ended "
                                 "unexpectedly.")

            n_token = self.next_token(current_tokens, allowed_next_tokens)
            if n_token not in allowed_next_tokens:
                raise ValueError(
                    f"Masked decoding invariant broken: {n_token}"
                    f"not in {allowed_next_tokens}"
                )
            best_option.append(n_token)
            current_tokens.append(n_token)

            candidates = [
                opt for opt in valid_option
                if len(opt) >= len(best_option)
                and opt[:len(best_option)] == best_option
            ]

    def get_logits(self,
                   tokens: list[int],
                   mask: set[int] | None = None) -> list[float]:
        """Return model logits for ``tokens``, optionally applying a mask."""
        instructions: list[int] | None = (self.t_instruction
                                          if self.t_instruction else [])
        logits: list[float] = []
        full_input: list[int] = []
        if instructions:
            full_input = instructions + tokens
        else:
            full_input = tokens
        logits = self.llm.get_logits_from_input_ids(full_input)
        if mask:
            logits = self._apply_mask(mask, logits)

        return logits

    def _apply_mask(self,
                    mask: set[int],
                    logits: list[float]) -> list[float]:
        """Set forbidden token scores to negative infinity."""
        masked_logits: list[float] = len(logits) * [-float('inf')]
        for id in mask:
            if 0 <= id < len(logits):
                masked_logits[id] = logits[id]
        return masked_logits
