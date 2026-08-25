REQUEST: Processing...
📓'What is the sum of 2 and 3?'...

[LLM.next_token] called
[LLM.next_token] input token count: 110
[LLM.next_token] decoded input: 'You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nWhat is the sum of 2 and 3?\n Respond with only one label: A, B, C.'
[LLM.next_token] allowed tokens: [(32, 'A'), (33, 'B'), (34, 'C')]

[LLM.get_logits] sending request to llm_sdk
[LLM.get_logits] prompt token count: 110
[LLM.get_logits] full input token count: 110
[LLM.get_logits] full decoded input: 'You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nWhat is the sum of 2 and 3?\n Respond with only one label: A, B, C.'
[LLM.get_logits] mask applied to logits
[LLM.next_token] selected token id: 32
[LLM.next_token] selected token text: 'A'

{"name": "fn_add_numbers", "arguments": {"a": 2, "b": 3}
<|im_start|>user
What is the sum of 2 and 3?
<|im_end|>
<|im_start|>assistant
<tool_call>
{"name": "fn_add_numbers", "arguments": {"a": 2, "b": 3}
}
⏱️ Prompt time: 5.87s
📓'What is the sum of 265 and 345?'...

[LLM.next_token] called
[LLM.next_token] input token count: 114
[LLM.next_token] decoded input: 'You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nWhat is the sum of 265 and 345?\n Respond with only one label: A, B, C.'
[LLM.next_token] allowed tokens: [(32, 'A'), (33, 'B'), (34, 'C')]

[LLM.get_logits] sending request to llm_sdk
[LLM.get_logits] prompt token count: 114
[LLM.get_logits] full input token count: 114
[LLM.get_logits] full decoded input: 'You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nWhat is the sum of 265 and 345?\n Respond with only one label: A, B, C.'
[LLM.get_logits] mask applied to logits
[LLM.next_token] selected token id: 32
[LLM.next_token] selected token text: 'A'

{"name": "fn_add_numbers", "arguments": {"a": 265, "b": 345}
<|im_start|>user
What is the sum of 265 and 345?
<|im_end|>
<|im_start|>assistant
<tool_call>
{"name": "fn_add_numbers", "arguments": {"a": 265, "b": 345}
}
⏱️ Prompt time: 2.44s
📓'Greet shrek'...

[LLM.next_token] called
[LLM.next_token] input token count: 104
[LLM.next_token] decoded input: 'You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nGreet shrek\n Respond with only one label: A, B, C.'
[LLM.next_token] allowed tokens: [(32, 'A'), (33, 'B'), (34, 'C')]

[LLM.get_logits] sending request to llm_sdk
[LLM.get_logits] prompt token count: 104
[LLM.get_logits] full input token count: 104
[LLM.get_logits] full decoded input: 'You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nGreet shrek\n Respond with only one label: A, B, C.'
[LLM.get_logits] mask applied to logits
[LLM.next_token] selected token id: 32
[LLM.next_token] selected token text: 'A'

{"name": "fn_add_numbers", "arguments": {"a": 0, "b": 0}
<|im_start|>user
Greet shrek
<|im_end|>
<|im_start|>assistant
<tool_call>
{"name": "fn_add_numbers", "arguments": {"a": 0, "b": 0}
}
⏱️ Prompt time: 2.04s
📓'Greet john'...

[LLM.next_token] called
[LLM.next_token] input token count: 103
[LLM.next_token] decoded input: 'You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nGreet john\n Respond with only one label: A, B, C.'
[LLM.next_token] allowed tokens: [(32, 'A'), (33, 'B'), (34, 'C')]

[LLM.get_logits] sending request to llm_sdk
[LLM.get_logits] prompt token count: 103
[LLM.get_logits] full input token count: 103
[LLM.get_logits] full decoded input: 'You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nGreet john\n Respond with only one label: A, B, C.'
[LLM.get_logits] mask applied to logits
[LLM.next_token] selected token id: 33
[LLM.next_token] selected token text: 'B'

{"name": "fn_greet", "arguments": {"name": "john"}
<|im_start|>user
Greet john
<|im_end|>
<|im_start|>assistant
<tool_call>
{"name": "fn_greet", "arguments": {"name": "john"}
}
⏱️ Prompt time: 1.84s
📓'Reverse the string 'hello''...

[LLM.next_token] called
[LLM.next_token] input token count: 105
[LLM.next_token] decoded input: "You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nReverse the string 'hello'\n Respond with only one label: A, B, C."
[LLM.next_token] allowed tokens: [(32, 'A'), (33, 'B'), (34, 'C')]

[LLM.get_logits] sending request to llm_sdk
[LLM.get_logits] prompt token count: 105
[LLM.get_logits] full input token count: 105
[LLM.get_logits] full decoded input: "You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nReverse the string 'hello'\n Respond with only one label: A, B, C."
[LLM.get_logits] mask applied to logits
[LLM.next_token] selected token id: 32
[LLM.next_token] selected token text: 'A'

{"name": "fn_add_numbers", "arguments": {"a": 0, "b": 0}
<|im_start|>user
Reverse the string 'hello'
<|im_end|>
<|im_start|>assistant
<tool_call>
{"name": "fn_add_numbers", "arguments": {"a": 0, "b": 0}
}
⏱️ Prompt time: 1.83s
📓'Reverse the string 'world''...

[LLM.next_token] called
[LLM.next_token] input token count: 105
[LLM.next_token] decoded input: "You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nReverse the string 'world'\n Respond with only one label: A, B, C."
[LLM.next_token] allowed tokens: [(32, 'A'), (33, 'B'), (34, 'C')]

[LLM.get_logits] sending request to llm_sdk
[LLM.get_logits] prompt token count: 105
[LLM.get_logits] full input token count: 105
[LLM.get_logits] full decoded input: "You are selecting the best function for a user request. \nAvailable functions:\nA: fn_add_numbers - Add two numbers together and return their sum. Parameters: a: number, b: number.\nB: fn_greet - Generate a greeting message for a person by name. Parameters: name: string.\nC: fn_reverse_string - Reverse a string and return the reversed result. Parameters: s: string.\n User request:\nReverse the string 'world'\n Respond with only one label: A, B, C."
[LLM.get_logits] mask applied to logits
[LLM.next_token] selected token id: 32
[LLM.next_token] selected token text: 'A'

{"name": "fn_add_numbers", "arguments": {"a": 0, "b": 0}
<|im_start|>user
Reverse the string 'world'
<|im_end|>
<|im_start|>assistant
<tool_call>
{"name": "fn_add_numbers", "arguments": {"a": 0, "b": 0}
}
⏱️ Prompt time: 1.85s
⏱️ Prompt processing total: {processing_end - processing_start:.2f}s
Run: 0 minutes
⏱️ Total run: 43.82s
Run: 0 minutes
⚙️ Programme finished...