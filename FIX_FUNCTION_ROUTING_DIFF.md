# Corrección mínima del bug de routing

## Objetivo

Corregir el enrutamiento de funciones **sin tocar `llm-sdk`** y **sin ampliar el alcance** a parsing, argumentos o schemas.

## Problema observado

Hoy el routing se decide en `src/llm.py` con una selección **greedy token a token** (`next_option`). En la práctica, eso sesga la elección hacia una sola ruta y termina enviando prompts distintos a `fn_get_square_root`, como ya se ve en `data/output/function_calls*.json`.

## Alcance

**Solo** cambiar:

- `src/llm.py`
- `src/call_me_maybe.py`

**No cambiar**:

- `llm_sdk`
- `src/function.py`
- inferencia de argumentos
- formato de salida

---

## 1) `src/llm.py`

### Qué remover

Remover la implementación actual de `next_option`, que construye la opción paso a paso:

```py
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
```

### Qué agregar

Reemplazarlo por scoring de **cada opción completa** usando la probabilidad acumulada de sus tokens:

```py
    def next_option(
        self,
        tokens: list[int],
        mask_options: list[list[int]]
    ) -> list[int]:
        """Return the highest-scoring full option."""
        if not mask_options:
            raise ValueError("mask_options cannot be empty")

        best_option: list[int] | None = None
        best_score = -float('inf')

        for option in mask_options:
            score = self._score_option(tokens, option)
            if score > best_score:
                best_score = score
                best_option = option

        if best_option is None:
            raise ValueError("No valid option could be scored")

        return best_option

    def _score_option(self, context: list[int], option: list[int]) -> float:
        """Score one full candidate by cumulative log-probability."""
        score = 0.0
        running_context = list(context)

        for token in option:
            logits = np.asarray(
                self.get_logits(running_context),
                dtype=np.float64,
            )

            if not 0 <= token < len(logits):
                return -float('inf')

            max_logit = np.max(logits)
            shifted = logits - max_logit
            log_probs = shifted - np.log(np.exp(shifted).sum())

            score += float(log_probs[token])
            running_context.append(token)

        return score
```

### Cambio adicional en `get_logits`

Si quieres corregir también el orden del contexto, cambia esto:

```py
        if instructions:
            full_input = tokens + instructions
        else:
            full_input = tokens
```

por esto:

```py
        if instructions:
            full_input = instructions + tokens
        else:
            full_input = tokens
```

### Intención del cambio

El LLM ya no “arma” el nombre de la función con una decisión local por token.  
Ahora compara secuencias completas y elige la mejor opción global para ese contexto.

---

## 2) `src/call_me_maybe.py`

### Qué remover

No hace falta tocar la lógica de argumentos.  
Solo reemplazar el bloque de routing dentro de `process_prompt`.

Bloque actual:

```py
        self.set_instructions()
        func_names = [f.t_name for f in self.functions.values()]
        func_name = self.llm.next_option(tokens, func_names)
        func = self.functions[self.encoder.decode(func_name)]
```

### Qué agregar

Usar nombres más explícitos y validar el nombre resuelto:

```py
        self.set_instructions()
        func_token_options = [f.t_name for f in self.functions.values()]
        selected_name_tokens = self.llm.next_option(tokens, func_token_options)
        selected_name = self.encoder.decode(selected_name_tokens)

        if selected_name not in self.functions:
            raise ValueError(f"Unknown routed function: {selected_name}")

        func = self.functions[selected_name]
```

### Mejora recomendada en `__init__`

Ahora mismo las definiciones quedan demasiado pegadas:

```py
        t_definitions = [t for f in functions.values()
                         for t in f.t_definition]
```

Haz al menos esto:

```py
        t_definitions = []
        for i, f in enumerate(functions.values()):
            if i > 0:
                t_definitions.extend(encoder.encode("\n"))
            t_definitions.extend(f.t_definition)
```

Si quieres algo un poco más robusto, usa una lista JSON completa, pero para el fix mínimo esto ya mejora bastante el bloque `<tools>`.

### Qué mantener igual

Dejar intacto todo lo demás en `process_prompt`, especialmente:

- construcción del prompt
- `self.set_instructions(func)`
- `add_args(...)`
- fallback de `json.loads(...)`
- `FunctionResponse(...)`

---

## Flujo esperado después del cambio

1. `process_prompt()` construye el contexto hasta `{"name": "`.
2. `CallMeMaybe` entrega a `LLM.next_option(...)` la lista de nombres de función tokenizados.
3. `LLM.next_option(...)` puntúa **cada nombre completo** y devuelve el mejor.
4. `CallMeMaybe` resuelve ese nombre a `FunctionDefinition`.
5. Solo entonces se restringe el contexto a esa función y se generan argumentos con la lógica actual.
6. La salida final sigue siendo el mismo JSON serializado.

---

## Resultado esperado

Con este cambio mínimo:

- `What is the sum of 2 and 3?` debe rutear a `fn_add_numbers`
- `Greet shrek` debe rutear a `fn_greet`
- `Reverse the string 'hello'` debe rutear a `fn_reverse_string`
- `What is the square root of 16?` debe rutear a `fn_get_square_root`
- prompts de reemplazo deben rutear a `fn_substitute_string_with_regex`

---

## Orden recomendado de implementación

1. Cambia `get_logits()` para corregir el orden del contexto.
2. Reemplaza `next_option()` por scoring de opción completa.
3. Ajusta `process_prompt()` para usar la selección resultante de forma explícita.
4. Añade separadores entre definiciones de tools en `__init__`.

---

## Nota de alcance

Si después de este cambio el modelo siguiera fallando en casos semánticos concretos, el siguiente paso correcto sería mejorar el router en `CallMeMaybe`.  
Pero ESO ya sería otra intervención.

Para este fix, la corrección mínima y limpia es:

- corregir el contexto
- cambiar el routing greedy por scoring de opción completa
- separar mejor las tools
