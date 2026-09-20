RUN = uv run python -m src

run:
	$(RUN) \
		--functions_definition data/input/functions_definition.json \
		--input data/input/function_calling_tests.json \
		--output data/output/function_calls.json

test:
	$(RUN) \
		--functions_definition data/input/tests/function_def_test1.json \
		--input data/input/tests/prompts_test1.json \
		--output data/output/function_calls.json
# 	$(RUN) \
# 		--functions_definition data/input/tests/function_empty_array.json \
# 		--input data/input/function_calling_tests.json \
# 		--output data/output/function_calls.json 
# 	$(RUN) \
# 		--functions_definition data/input/tests/function_empty_array.json \
# 		--input data/input/function_calling_tests.json \
# 		--output data/output/function_calls.json 
# 	$(RUN) \
# 		--functions_definition data/input/tests/function_empty_str.json \
# 		--input data/input/function_calling_tests.json \
# 		--output data/output/function_calls.json 
# 	$(RUN) \
# 		--functions_definition data/input/tests/function_error_json.json \
# 		--input data/input/function_calling_tests.json \
# 		--output data/output/function_calls.json 
# 	$(RUN) \
# 		--functions_definition data/input/functions_definition.json \
# 		--input data/input/tests/prompt_empty_array.json \
# 		--output data/output/function_calls.json 
# 	$(RUN) \
# 		--functions_definition data/input/functions_definition.json \
# 		--input data/input/tests/prompt_empty_str.json \
# 		--output data/output/function_calls.json 
# 	$(RUN) \
# 		--functions_definition data/input/functions_definition.json \
# 		--input  data/input/tests/prompt_error_json.json \
# 		--output data/output/function_calls.json 
# 	$(RUN) \
# 			--functions_definition data/input/functions_definition.json \
# 			--input data/input/tests/non_exist.json \
# 			--output data/output/function_calls.json
# 	$(RUN) \
# 			--functions_definition data/input/functions_definition.json \
# 			--input data/input/tests/prompt_escape.json \
# 			--output data/output/function_calls.json 

install:
	uv sync --no-install-project

debug:
	uv run python -m pdb -m src

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -name "*.pyc" -delete

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict


.PHONY: install run debug clean lint lint-strict

