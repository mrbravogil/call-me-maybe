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
    params_schema: dict[str, dict[str, Any]] = Field(...)
    required_params: list[str]
    t_definition: list[int]

    def __init__(self,
                 function: dict[str, Any],
                 encoder: Encoder):
        name = function['name']
        description = function['description']
        params_schema = function['parameters']
        params = {k: v['type'] for k, v in params_schema.items()}
        required_params = list(params_schema.keys())

        t_definition = encoder.encode(json.dumps({
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    k: v
                    for k, v in params_schema.items()
                },
                "required": required_params
            }
        }))

        super().__init__(name=name,
                         t_name=encoder.encode(name),
                         description=description,
                         t_description=encoder.encode(description),
                         params_schema=params_schema,
                         params=params,
                         required_params=required_params,
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

    @staticmethod
    def _cast_argument_type(expected_type: str, value: Any) -> Any:
        """Casts a value to the expected function parameter type."""
        if expected_type == 'string':
            return str(value)
        if expected_type == 'number':
            if isinstance(value, bool):
                raise ValueError(f"cannot cast {value!r} to number.")
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                return float(value)
            raise ValueError(f"cannot cast {value!r} to number.")

        if expected_type == 'integer':
            if isinstance(value, bool):
                raise ValueError(f"cannot cast {value!r} to integer.")
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                if value.is_integer():
                    return int(value)
                raise ValueError(f"cannot cast {value!r} to integer.")
            if isinstance(value, str):
                parsed = float(value)
                if parsed.is_integer():
                    return int(parsed)
                raise ValueError(f"cannot cast {value!r} to integer.")
            raise ValueError(f"cannot cast {value!r} to integer.")

        if expected_type == 'boolean':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered == 'true':
                    return True
                if lowered == 'false':
                    return False
            raise ValueError(f"cannot cast {value!r} to boolean")

        return value

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Validates and normalizes arguments produced by the LLM."""
        if not isinstance(arguments, dict):
            raise ValueError('[validate_arguments] arguments must be'
                             ' a JSON object.')

        extra_keys = set(arguments.keys()) - set(self.required_params)
        if extra_keys:
            raise ValueError('[validate_arguments] unexpected arguments: '
                             f'{sorted(extra_keys)}.')

        missing_keys = [name for name in self.required_params
                        if name not in arguments]
        if missing_keys:
            raise ValueError('[validate_arguments] missing required arguments:'
                             f' {missing_keys}.')

        normalized: dict[str, Any] = {}
        for name in self.required_params:
            expected_type = self.params[name]
            normalized[name] = self._cast_argument_type(
                expected_type,
                arguments[name],
            )

        if self.name == 'fn_get_square_root':
            first_value = next(iter(normalized.values()))
            if first_value < 0:
                raise ValueError('[validate_arguments] square root input'
                                 ' cannot be negative.')

        return normalized

    @model_validator(mode="after")
    def validate_function(self) -> Self:
        if not self.name.strip():
            raise ValueError("name cannot be empty")

        if not self.description.strip():
            raise ValueError("description cannot be empty")

        if not self.params:
            raise ValueError("parameters cannot be empty")

        for name, type in self.params.items():
            if not name.strip():
                raise ValueError("parameter name cannot be empty")
            if not isinstance(type, str):
                raise ValueError(f"parameter '{name}' cannot be empty")

            schema = self.params_schema.get(name)
            if not isinstance(schema, dict):
                raise ValueError(f"parameter '{name} must "
                                 "have a valid schema.")

        return self


class FunctionResponse(BaseModel):
    """Pydantic model representing a generated function call result."""

    prompt: str = Field(...)
    name: str = Field(...)
    parameters: dict[str, Any] = Field(...)

    def json_schema(self) -> str:
        return json.dumps(self.model_dump())

    @model_validator(mode="after")
    def validate_add_numbers(self) -> Self:
        if self.name == "fn_add_numbers" or self.name == "fn_get_square_root":
            for param in self.parameters.values():
                if not isinstance(param, (int, float)):
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
