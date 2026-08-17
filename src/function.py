from pydantic import BaseModel, Field, model_validator
from typing import Any
from typing_extensions import Self


class FunctionDefinition(BaseModel):
    """Pydantic model representing a function definition schema."""

    name: str = Field(...)
    description: str = Field(...)
    parameters: dict[str, Any] = Field(...)
    returns: dict[str, Any] = Field(...)


class FunctionResponse(BaseModel):
    """Pydantic model representing a generated function call result."""

    prompt: str = Field(...)
    name: str = Field(...)
    parameters: dict[str, Any] = Field(...)

    @model_validator(mode="after")
    def validate_add_numbers(self) -> Self:
        if self.name == "fn_add_numbers" or self.name == "fn_get_square_root":
            for param in self.parameters.values():
                if not isinstance(param, int):
                    raise ValueError("All parameters of fn_add_numbers, "
                                     "fn_get_square_root "
                                     "must be numbers.")
        return self

    @model_validator(mode="after")
    def validate_str_function(self) -> Self:
        if (self.name == "fn_greet" or self.name == "fn_reverse_string"
                or self.name == "fn_substitute_string_with_regex"):
            for param in self.parameters.values():
                if not isinstance(param, str):
                    raise ValueError("All parameters of fn_greet, "
                                     "fn_reverse_string, "
                                     "fn_substitute_string_with_regex "
                                     "must be strings.")
        return self
