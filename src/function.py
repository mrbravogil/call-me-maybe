from pydantic import BaseModel, Field, model_validator
from typing import Any
import json
from typing_extensions import Self
from src.encoder import Encoder


class FunctionDefinition(BaseModel):
    """Pydantic model representing a function definition schema."""

    _name: str = Field(...)
    _t_name: list[int]
    _description: str = Field(...)
    _t_description: list[int]
    _params: dict[str, Any] = Field(...)
    _t_params: dict[str, list[int]]
    _returns: dict[str, Any] = Field(...)
    _t_returns: dict[str, list[int]]
    _t_definition: list[int]

    def __init__(self,
                 function: dict[str, Any],
                 encoder: Encoder):
        self._name = function['name']
        self._t_name = encoder.encode(self._name)
        self._description = function['description']
        self._t_description = encoder.encode(self._description)
        self._params = {k: v['type']
                        for k, v in function['parameters'].items()}
        self._t_params = {k: encoder.encode(v['type'])
                          for k, v in function['parameters'].items()}
        self._returns = {k: v['type']
                         for k, v in function['returns'].items()}
        self._t_returns = {k: encoder.encode(v['type'])
                           for k, v in function['returns'].items()}
        self._t_definition = encoder.encode(self._json_schema())

    def _json_schema(self) -> str:
        return json.dumps({
            "name": self._name,
            "description": self._description,
            "parameters": {
                "type": "object",
                "properties": {
                    k: {"type": v}
                    for k, v in self._params.items()
                },
                "required": list(self._params.keys())
            }
        })


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
