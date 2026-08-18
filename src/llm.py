import numpy as np
from pydantic import BaseModel
from llm_sdk.llm_sdk import Small_LLM_Model
from src.encoder import Encoder


class LLM(BaseModel):
    _llm: Small_LLM_Model
    _encoder: Encoder
    _t_instruction: list[int] | None

    def __init__(self, llm: Small_LLM_Model, encoder: Encoder):
        print("LLM: Building")
        super().__init__()
        self._llm = llm
        self._encoder = encoder
        self._t_instruction = None
        print("LLM: Created...")

    def set_instructions(self, instructions: list[int] | str) -> None:
        """Sets the instruction with information for LLM."""
        if isinstance(instructions, str):
            instructions = self._encoder.encode(instructions)
        self._t_instruction = instructions

    def next_token(self,
                   tokens: list[int],
                   mask: set[int] | None = None) -> int:
        """Returns the next token for the provided tokens."""
        logits = self.get_logits(tokens, mask)
        next_token = int(np.argmax(logits))
        return next_token

    def next_option(
        self,
        tokens: list[int],
        mask_options: list[list[int]]
    ) -> list[int]:
        """Return the best allowed option."""
        results: list[int] = []
        context: list[int] = tokens + results
        for option in mask_options:
            allowed_options: set[int] = {option[0] for option in mask_options}
            next_token: int = self.next_token(context, allowed_options)
            results.append(next_token)
            context.append(next_token)
            mask_options = [option[1:]
                            for option in mask_options
                            if option[0] == next_token
                            and len(option) > 1]
        return results

    def get_logits(self,
                   tokens: list[int],
                   mask: set[int] | None = None) -> list[float]:
        """
        Returns the list of logits for provided tokens.
        Applies the mask optionally.
        """
        instructions: list[int] | None = (self._t_instruction
                                          if self._t_instruction
                                          else [])
        logits: list[float] = []
        if instructions:
            log = instructions + tokens
            logits = self._llm.get_logits_from_input_ids(log)
        else:
            logits = self._llm.get_logits_from_input_ids(tokens)

        if mask:
            logits = self._apply_mask(mask, logits)

        return logits

    def _apply_mask(self,
                    mask: set[int],
                    logits: list[float]) -> list[float]:
        """
        Returns logits with mask applied by setting all forbidden
        token scores to -infinity.
        """
        masked_logits: list[float] = len(logits) * [-float('inf')]
        for id in mask:
            masked_logits[id] = logits[id]
        return masked_logits
