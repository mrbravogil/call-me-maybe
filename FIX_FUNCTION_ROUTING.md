# Guía breve para corregir el bug de enrutamiento de tools/functions sin tocar `llm-sdk`

## Resumen

El bug NO está en `llm_sdk`. Está en la capa de enrutamiento de este repositorio.

Hay dos problemas principales:

1. El contexto de instrucciones y tools se usa mal al momento de puntuar la siguiente salida del modelo.
2. La selección de función se hace de forma greedy por token, en lugar de comparar candidatos completos.

Además, los argumentos no salen realmente de una tool call completa del modelo; se rellenan con heurísticas locales.

---

## Dónde cambiar

| Archivo | Método | Qué cambiar |
|---|---|---|
| `src/llm.py` | `get_logits` | Cambiar el orden del contexto para que las instrucciones vayan antes del prompt/candidate context. |
| `src/llm.py` | `next_option` o nuevo método | Dejar de seleccionar la función token a token con greedy puro. |
| `src/call_me_maybe.py` | `__init__` | Formatear mejor el bloque de tools para que las definiciones no queden “pegadas”. |
| `src/call_me_maybe.py` | `process_prompt` | Separar: primero seleccionar función, después construir argumentos y JSON final. |
| `src/call_me_maybe.py` | nuevo helper `_select_function` | Puntuar cada función completa y elegir la de mejor score total. |

No hace falta tocar:

- `llm_sdk/llm_sdk/__init__.py`

---

## Problema 1: orden incorrecto del contexto

### Estado actual

En `src/llm.py`:

```python
if instructions:
    full_input = tokens + instructions
```

Eso es conceptualmente incorrecto. Estás mandando primero el prompt parcial y luego las instrucciones del sistema/tools.

### Qué debe pasar

El modelo debe ver:

1. instrucciones del sistema
2. tools
3. prompt del usuario
4. prefijo del assistant/tool call

### Cambio recomendado

En `LLM.get_logits(...)`, usar:

```python
full_input = instructions + tokens
```

si hay instrucciones activas.

---

## Problema 2: selección greedy por prefijo

### Estado actual

En `src/llm.py -> next_option()` eliges el nombre de la función token por token:

- miras los tokens permitidos en esa posición
- haces `argmax`
- te quedas con ese camino

Eso colapsa fácilmente a una sola función cuando el contexto no está bien armado o cuando los nombres comparten prefijos como `fn_...`.

### Qué cambiar

NO debes elegir por el “mejor siguiente token”.

Debes:

1. tomar cada función candidata completa
2. recorrer todos sus tokens
3. acumular el score de cada token esperado
4. quedarte con la función con mejor score total

---

## Problema 3: tools poco claras en el prompt

### Estado actual

En `src/call_me_maybe.py`, `t_definitions` se construye concatenando todas las definiciones:

```python
t_definitions = [t for f in functions.values() for t in f.t_definition]
```

Eso deja múltiples JSON seguidos, sin una estructura clara entre ellos.

### Qué cambiar

Construir el bloque con separadores reales, por ejemplo con saltos de línea entre definiciones, o mejor aún con una lista JSON clara.

Ejemplo conceptual:

```text
<tools>
{tool_1_json}
{tool_2_json}
{tool_3_json}
</tools>
```

o:

```text
<tools>
[
  {tool_1_json},
  {tool_2_json},
  {tool_3_json}
]
</tools>
```

La segunda opción suele ser más robusta.

---

## Plan de cambio paso a paso

### 1. Corregir el orden del input en `src/llm.py`

Cambiar la construcción de `full_input` para que las instrucciones vayan primero.

### 2. Mejorar el bloque de tools en `src/call_me_maybe.py`

Generar las definiciones con separadores claros.

### 3. Crear `_select_function(prompt)`

Ese método debe:

- preparar el contexto base
- puntuar cada función candidata completa
- devolver la mejor función

### 4. Cambiar `process_prompt()`

En lugar de:

```python
func_name = self.llm.next_option(tokens, func_names)
func = self.functions[self.encoder.decode(func_name)]
```

usar algo como:

```python
func = self._select_function(prompt)
```

### 5. Mantener `_infer_arguments()` por ahora

Si no quieres ampliar alcance, puedes mantener la inferencia heurística de argumentos.

OJO: eso no convierte el sistema en un tool-calling completo. Solo arregla la adjudicación correcta de función, que ahora es el bug principal.

---

## Pseudocódigo en español

### Pseudocódigo para puntuar funciones completas

```text
función seleccionar_función(prompt):
    contexto_base = construir_contexto_base(prompt)

    mejor_función = null
    mejor_score = -infinito

    para cada función en catálogo_de_funciones:
        contexto = copia(contexto_base)
        score_total = 0

        para cada token en tokens_del_nombre_de_la_función:
            logits = obtener_logits(contexto)
            score_token = logits[token]
            score_total = score_total + score_token
            agregar token al contexto

        si score_total > mejor_score:
            mejor_score = score_total
            mejor_función = función

    retornar mejor_función
```

### Pseudocódigo para construir el flujo principal

```text
función process_prompt(prompt_original):
    prompt_escapado = escapar(prompt_original)
    función_elegida = seleccionar_función(prompt_escapado)
    argumentos = inferir_argumentos(función_elegida, prompt_original)
    respuesta = construir_json_final(prompt_escapado, función_elegida, argumentos)
    retornar respuesta
```

### Pseudocódigo para el contexto correcto

```text
función obtener_logits(tokens_prompt):
    si existen instrucciones:
        input_completo = instrucciones + tokens_prompt
    si no:
        input_completo = tokens_prompt

    retornar logits_del_modelo(input_completo)
```

### Pseudocódigo para tools bien formateadas

```text
función construir_tools(functions):
    definiciones = []

    para cada función en functions:
        definiciones.agregar(json_de_la_función)

    tools_text = unir_con_separador(definiciones, "\n")
    retornar tools_text
```

---

## Comportamiento esperado después del fix

Estos prompts deberían rutear así:

- `What is the sum of 2 and 3?` → `fn_add_numbers`
- `What is the sum of 265 and 345?` → `fn_add_numbers`
- `Greet shrek` → `fn_greet`
- `Greet john` → `fn_greet`
- `Reverse the string 'hello'` → `fn_reverse_string`
- `Reverse the string 'world'` → `fn_reverse_string`
- `What is the square root of 16?` → `fn_get_square_root`
- `Calculate the square root of 144` → `fn_get_square_root`
- `Replace all numbers in "Hello 34 I'm 233 years old" with NUMBERS` → `fn_substitute_string_with_regex`
- `Replace all vowels in 'Programming is fun' with asterisks` → `fn_substitute_string_with_regex`
- `Substitute the word 'cat' with 'dog' in 'The cat sat on the mat with another cat'` → `fn_substitute_string_with_regex`

---

## Recomendación práctica

Si quieres el fix mínimo y más seguro, haz SOLO esto:

1. Cambia `tokens + instructions` por `instructions + tokens` en `src/llm.py`.
2. Agrega un selector por score completo de función.
3. Haz que `process_prompt()` use ese selector.
4. Mejora el bloque `<tools>` para que tenga separadores claros.

Con eso deberías corregir el problema de que siempre elija la misma función sin tocar `llm-sdk`.
