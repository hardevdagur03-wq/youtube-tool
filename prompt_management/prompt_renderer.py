from __future__ import annotations

import re
from typing import Any

from prompt_management.prompt_loader import PromptLoader
from prompt_management.prompt_cache import PromptCache


class PromptRenderer:
    VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")
    PARTIAL_PATTERN = re.compile(r"\{\{>(\w+)\}\}")

    def __init__(self, loader: PromptLoader, cache: PromptCache | None = None):
        self._loader = loader
        self._cache = cache or PromptCache()
        self._compiled_cache: dict[str, str] = {}

    def render(self, prompt_name: str, variables: dict[str, Any]) -> str | None:
        cache_key = self._make_cache_key(prompt_name, variables)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        raw = self._loader.load_raw(prompt_name)
        if raw is None:
            return None

        rendered = self._render_template(raw, variables)
        self._cache.set(cache_key, rendered)
        return rendered

    def render_content(self, content: str, variables: dict[str, Any]) -> str:
        return self._render_template(content, variables)

    def render_partial(self, partial_name: str, variables: dict[str, Any]) -> str | None:
        content = self._loader.load_content(partial_name)
        if content is None:
            return None
        return self._render_template(content, variables)

    def resolve_partials(self, template_content: str, variables: dict[str, Any]) -> str:
        def _replace_partial(m: re.Match) -> str:
            partial_name = m.group(1)
            partial_content = self._loader.load_content(partial_name)
            if partial_content is None:
                partial_content = self._loader.load_content(f"shared/{partial_name}")
            if partial_content is None:
                partial_content = self._loader.load_content(f"partials/{partial_name}")
            if partial_content is None:
                return f"<!-- missing partial: {partial_name} -->"
            return self._render_template(partial_content, variables)

        return self.PARTIAL_PATTERN.sub(_replace_partial, template_content)

    def resolve_variables(self, content: str, variables: dict[str, Any]) -> str:
        def _replace_var(m: re.Match) -> str:
            var_name = m.group(1)
            if var_name in variables:
                val = variables[var_name]
                if isinstance(val, (dict, list)):
                    import json
                    return json.dumps(val)
                return str(val)
            return f"{{{{{var_name}}}}}"

        return self.VARIABLE_PATTERN.sub(_replace_var, content)

    def _find_matching_pairs(self, content: str, tag: str) -> list[tuple[int, int, str, str]]:
        open_pat = re.compile(r"\{\{#" + re.escape(tag) + r" (\w+)\}\}")
        close_tag = "{{/" + tag + "}}"
        opens = [(m.start(), m.end(), m.group(1)) for m in open_pat.finditer(content)]
        closes = [m.start() for m in re.finditer(re.escape(close_tag), content)]
        if not opens or not closes:
            return []
        events: list[tuple[int, bool, int, str | None]] = []
        for start, end, var_name in opens:
            events.append((start, True, end, var_name))
        for pos in closes:
            events.append((pos, False, pos + len(close_tag), None))
        events.sort(key=lambda x: x[0])
        stack: list[tuple[int, int, str]] = []
        pairs: list[tuple[int, int, str, str]] = []
        for pos, is_open, end, var_name in events:
            if is_open:
                stack.append((pos, end, var_name))
            else:
                if not stack:
                    continue
                open_pos, open_end, vname = stack.pop()
                inner = content[open_end:pos]
                pairs.append((open_pos, end, vname, inner))
        return pairs

    def resolve_conditionals(self, content: str, variables: dict[str, Any]) -> str:
        loop_pairs = self._find_matching_pairs(content, "each")
        loop_ranges = [(s, e) for s, e, _, _ in loop_pairs]
        for _ in range(50):
            m = self._find_next_conditional(content, loop_ranges)
            if not m:
                break
            full_match, var_name, inner = m
            idx = content.index(full_match)
            if bool(variables.get(var_name)):
                replacement = self._render_template(inner, variables)
            else:
                replacement = ""
            content = content[:idx] + replacement + content[idx + len(full_match):]
        return content

    def resolve_loops(self, content: str, variables: dict[str, Any]) -> str:
        for _ in range(50):
            m = self._find_next_loop(content)
            if not m:
                break
            full_match, var_name, template = m
            items = variables.get(var_name, [])
            if not isinstance(items, list) or not items:
                idx = content.index(full_match)
                content = content[:idx] + "" + content[idx + len(full_match):]
                continue
            parts = []
            for item in items:
                if isinstance(item, dict):
                    merged = {**variables, **item}
                    rendered = self._render_template(template, merged)
                else:
                    rendered = self._render_template(template, {**variables, "item": item})
                if rendered:
                    parts.append(rendered)
            idx = content.index(full_match)
            content = content[:idx] + "\n".join(parts) + content[idx + len(full_match):]
        return content

    def _find_next_conditional(self, content: str, loop_ranges: list[tuple[int, int]]) -> tuple[str, str, str] | None:
        pairs = self._find_matching_pairs(content, "if")
        for open_pos, close_end, var_name, inner in pairs:
            has_nested_if = bool(re.search(r"\{\{#if \w+\}\}", inner))
            has_nested_loop = bool(re.search(r"\{\{#each \w+\}\}", inner))
            if not has_nested_if and not has_nested_loop:
                inside_loop = any(s < open_pos < e for s, e in loop_ranges)
                if not inside_loop:
                    full_match = content[open_pos:close_end]
                    return (full_match, var_name, inner)
        return None

    def _find_next_loop(self, content: str) -> tuple[str, str, str] | None:
        pairs = self._find_matching_pairs(content, "each")
        for open_pos, close_end, var_name, inner in pairs:
            if not re.search(r"\{\{#each \w+\}\}", inner):
                full_match = content[open_pos:close_end]
                return (full_match, var_name, inner)
        return None

    def _render_template(self, template: str, variables: dict[str, Any]) -> str:
        result = template
        result = self.resolve_partials(result, variables)
        result = self.resolve_conditionals(result, variables)
        result = self.resolve_loops(result, variables)
        result = self.resolve_variables(result, variables)
        return result.strip()

    def _make_cache_key(self, prompt_name: str, variables: dict[str, Any]) -> str:
        import hashlib
        import json
        raw = f"{prompt_name}:{json.dumps(variables, sort_keys=True)}"
        return f"rendered:{hashlib.sha256(raw.encode()).hexdigest()[:32]}"

    def get_unresolved_variables(self, content: str) -> list[str]:
        return list(set(self.VARIABLE_PATTERN.findall(content)))

    def get_partial_refs(self, content: str) -> list[str]:
        return [m.group(1) for m in self.PARTIAL_PATTERN.finditer(content)]

    def get_conditional_vars(self, content: str) -> list[str]:
        return [m.group(1) for _, _, m, _ in self._find_matching_pairs(content, "if")]

    def compile_template(self, prompt_name: str) -> str | None:
        if prompt_name in self._compiled_cache:
            return self._compiled_cache[prompt_name]
        raw = self._loader.load_raw(prompt_name)
        if raw is None:
            return None
        pre_resolved = self.resolve_partials(raw, {})
        self._compiled_cache[prompt_name] = pre_resolved
        return pre_resolved

    def invalidate_cache(self, prompt_name: str | None = None) -> None:
        if prompt_name:
            self._compiled_cache.pop(prompt_name, None)
            self._cache.invalidate_pattern(f"rendered:*{prompt_name}*")
        else:
            self._compiled_cache.clear()
            self._cache.clear()
