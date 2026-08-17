import numpy as np
from pydantic import BaseModel
from llm_sdk.llm_sdk import Small_LLM_Model
from src.encoder import Encoder


class LLM(BaseModel):
    _llm: Small_LLM_Model
    _encoder: Encoder
    _t_instruction: list[int] | None

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
        masked_logits: list[float] = np.full(len(logits), -float('inf'))
        for id in mask:
            masked_logits[id] = logits[id]
        return masked_logits
