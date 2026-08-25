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
        print("\n[LLM.next_token] called")
        print(f"[LLM.next_token] input token count: {len(tokens)}")
        print("[LLM.next_token] decoded input: "
              f"{self.encoder.decode(tokens)!r}")
        if mask:
            decoded_mask = []
            for token_id in sorted(mask):
                try:
                    decoded_mask.append((token_id,
                                         self.encoder.decode([token_id])))
                except Exception:
                    decoded_mask.append((token_id, "<decode-error>"))
            print(f"[LLM.next_token] allowed tokens: {decoded_mask}")

        logits = self.get_logits(tokens, mask)
        selected_token = int(np.argmax(logits))
        try:
            decoded_next = self.encoder.decode([selected_token])
        except Exception:
            decoded_next = "<decode-error>"
        print(f"[LLM.next_token] selected token id: {selected_token}")
        print(f"[LLM.next_token] selected token text: {decoded_next!r}")
        return selected_token

    def next_option(
        self,
        tokens: list[int],
        mask_options: list[list[int]]
    ) -> list[int]:
        """Return the best allowed option."""
        if not mask_options:
            raise ValueError("LLM, next_option(): mask_options cannot "
                             "be empty.")

        candidates = [option[:] for option in mask_options]
        best_option: list[int] = []
        current_tokens = tokens[:]

        while True:
            if len(candidates) == 1 and len(best_option) == len(candidates):
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

    def score_options(
            self,
            tokens: list[int],
            options: dict[str, list[int]]
    ) -> str:
        """Return the label of the highest-scoring candidate option."""
        if not options:
            raise ValueError("LLM.score_options(): options cannot be empty.")

        best_label: str | None = None
        best_score: float = -float("inf")

        for label, option in options.items():
            score = self._score_option(tokens, option)
            if score > best_score:
                best_score = score
                best_label = label

        if best_label is None:
            raise ValueError("LLM.score_options(): no option could be scored.")

        return best_label

    def _score_option(self,
                      tokens: list[int],
                      options: list[int]) -> float:
        """Score one full candidate by cumulative log-probability."""
        score: float = 0.0
        current_context = tokens.copy()

        for token in options:
            logits = np.asarray(self.get_logits(current_context))

            if not 0 <= token < len(logits):
                return -float('inf')

            logits = logits - np.max(logits)
            log_probs = logits - np.log(np.sum(np.exp(logits)))
            score += float(log_probs[token])
            current_context.append(token)

        return score

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
        """
        Returns logits with mask applied by setting all forbidden
        token scores to -infinity.
        """
        masked_logits: list[float] = len(logits) * [-float('inf')]
        for id in mask:
            if 0 <= id < len(logits):
                masked_logits[id] = logits[id]
        return masked_logits
