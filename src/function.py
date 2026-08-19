from pydantic import BaseModel, Field, model_validator
from typing import Any
import json
from typing_extensions import Self
from src.encoder import Encoder


class FunctionDefinition(BaseModel):
    """Pydantic model representing a function definition schema."""

    name: str = Field(...)
    t_name: list[int]
    description: str = Field(...)
    t_description: list[int]
    params: dict[str, Any] = Field(...)
    t_params: dict[str, list[int]]
    t_definition: list[int]

    def __init__(self,
                 function: dict[str, Any],
                 encoder: Encoder):
        name = function['name']
        description = function['description']
        params = {k: v['type']
                  for k, v in function['parameters'].items()}
        t_params = {k: encoder.encode(v['type'])
                    for k, v in function['parameters'].items()}

        t_definition = encoder.encode(json.dumps({
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    k: {"type": v}
                    for k, v in params.items()
                },
                "required": list(params.keys())
            }
        }))

        super().__init__(name=name,
                         t_name=encoder.encode(name),
                         description=description,
                         t_description=encoder.encode(description),
                         params=params,
                         t_params=t_params,
                         t_definition=t_definition)

    def _json_schema(self) -> str:
        return json.dumps({
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    k: {"type": v}
                    for k, v in self.params.items()
                },
                "required": list(self.params.keys())
            }
        })


class FunctionResponse(BaseModel):
    """Pydantic model representing a generated function call result."""

    prompt: str = Field(...)
    name: str = Field(...)
    parameters: dict[str, Any] = Field(...)

    def json_schema(self) -> str:
        return json.dumps({
                    "prompt": self.prompt,
                    "name": self.name,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            k: {"type": v}
                            for k, v in self.parameters.items()
                        }
                    }
                })

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
