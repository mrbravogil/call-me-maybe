import numpy as np
from pydantic import BaseModel, ConfigDict
from src.encoder import Encoder
from llm_sdk.llm_sdk import Small_LLM_Model


class LLM(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    llm: Small_LLM_Model
    encoder: Encoder
    t_instruction: list[int] | None

    def __init__(self, llm: Small_LLM_Model, encoder: Encoder):
        print("\nLLM:")
        print("🛠️ Building...")
        super().__init__(
            llm=llm,
            encoder=encoder,
            t_instruction=None)
        print("✅Created...")

    def set_instructions(self, instructions: list[int] | str) -> None:
        """Sets the instruction with information for LLM."""
        if isinstance(instructions, str):
            instructions = self.encoder.encode(instructions)
        self.t_instruction = instructions

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
        context: list[int] = list(tokens)
        active_options: list[list[int]] = [
            opt[:] for opt in mask_options if opt
        ]

        attempts: int = 0
        while active_options and attempts < 64:
            allowed_options: set[int] = {opt[0] for opt in active_options}
            next_token: int = self.next_token(context, allowed_options)
            results.append(next_token)
            context.append(next_token)
            active_options = [
                opt[1:]
                for opt in active_options
                if opt[0] == next_token and len(opt) > 1
            ]

        return results

    def get_logits(self,
                   tokens: list[int],
                   mask: set[int] | None = None) -> list[float]:
        """
        Returns the list of logits for provided tokens.
        Applies the mask optionally.
        """
        instructions: list[int] | None = (self.t_instruction
                                          if self.t_instruction else [])
        logits: list[float] = []
        full_input: list[int] = []
        if instructions:
            full_input = tokens + instructions
        else:
            full_input = tokens
        logits = self.llm.get_logits_from_input_ids(full_input)
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
            if 0 <= id < len(logits):
                masked_logits[id] = logits[id]
        return masked_logits
