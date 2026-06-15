"""
AST-based static analysis for Python source files.

Provides complexity calculation, code-smell detection, and
file-level metrics without any external dependencies beyond
the Python standard library.
"""

from __future__ import annotations

import ast
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Branch-counting node types (cyclomatic complexity) ───────

_BRANCH_NODES = (
    ast.If,
    ast.For,
    ast.While,
    ast.Try,
    ast.ExceptHandler,
    ast.With,
    ast.Assert,
    ast.BoolOp,
)


def calculate_complexity(node: ast.AST) -> int:
    """Calculate an approximation of cyclomatic complexity.

    Counts branch/decision points in the AST sub-tree rooted at
    *node*.

    Args:
        node: Any AST node (usually a ``FunctionDef`` or ``Module``).

    Returns:
        Integer complexity score (minimum 1).
    """
    complexity = 1  # baseline path
    for child in ast.walk(node):
        if isinstance(child, _BRANCH_NODES):
            complexity += 1
        # Each `elif` is an extra branch inside an If
        if isinstance(child, ast.If) and hasattr(child, "orelse"):
            for alt in child.orelse:
                if isinstance(alt, ast.If):
                    complexity += 1
    return complexity


def _max_nesting_depth(node: ast.AST, current: int = 0) -> int:
    """Recursively compute maximum nesting depth of control-flow blocks."""
    max_depth = current
    nesting_types = (ast.If, ast.For, ast.While, ast.With, ast.Try)

    for child in ast.iter_child_nodes(node):
        if isinstance(child, nesting_types):
            max_depth = max(max_depth, _max_nesting_depth(child, current + 1))
        else:
            max_depth = max(max_depth, _max_nesting_depth(child, current))
    return max_depth


def parse_python_file(code: str) -> dict[str, Any]:
    """Parse a Python source string and extract structural metadata.

    Args:
        code: Raw Python source code.

    Returns:
        Dict with keys:
        - ``functions``: list of function descriptors
        - ``classes``: list of class descriptors
        - ``imports``: list of imported module names
        - ``total_complexity``: aggregate complexity score
        - ``has_errors``: whether parsing failed
    """
    result: dict[str, Any] = {
        "functions": [],
        "classes": [],
        "imports": [],
        "total_complexity": 0,
        "has_errors": False,
    }

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        logger.warning("Syntax error while parsing: %s", exc)
        result["has_errors"] = True
        return result

    for node in ast.walk(tree):
        # ── Functions / methods ──────────────────────────────
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_complexity = calculate_complexity(node)
            end_line = getattr(node, "end_lineno", node.lineno)
            func_info = {
                "name": node.name,
                "line": node.lineno,
                "end_line": end_line,
                "length": end_line - node.lineno + 1,
                "args": [arg.arg for arg in node.args.args],
                "has_docstring": (
                    isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Constant,))
                    and isinstance(node.body[0].value.value, str)
                    if node.body
                    else False
                ),
                "complexity": func_complexity,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            }
            result["functions"].append(func_info)
            result["total_complexity"] += func_complexity

        # ── Classes ──────────────────────────────────────────
        elif isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "line": node.lineno,
                "methods": [
                    n.name
                    for n in ast.walk(node)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ],
                "has_docstring": (
                    isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, (ast.Constant,))
                    and isinstance(node.body[0].value.value, str)
                    if node.body
                    else False
                ),
                "bases": [ast.dump(b) for b in node.bases],
            }
            result["classes"].append(class_info)

        # ── Imports ──────────────────────────────────────────
        elif isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                result["imports"].append(f"{module}.{alias.name}")

    return result


def parse_javascript_file(code: str) -> dict[str, Any]:
    """Parse a JavaScript/TypeScript source string to extract metadata using heuristics.

    Args:
        code: Raw JS/TS source code.

    Returns:
        Dict with keys:
        - ``functions``: list of function descriptors
        - ``classes``: list of class descriptors
        - ``imports``: list of imported module names
        - ``total_complexity``: aggregate complexity score
        - ``has_errors``: whether parsing failed
    """
    result: dict[str, Any] = {
        "functions": [],
        "classes": [],
        "imports": [],
        "total_complexity": 1,
        "has_errors": False,
    }

    # Regex patterns
    # 1. Standard function: function name(...) or async function name(...)
    # 2. Arrow function assignment: const name = (...) => or let name = async(...) =>
    # 3. Class method: name(...) {
    func_pattern = re.compile(
        r'\b(?:function\s+([a-zA-Z0-9_$]+)\s*\()|'
        r'\b(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\(.*?\)\s*=>|'
        r'\b([a-zA-Z0-9_$]+)\s*\((?:[^()]*|\([^()]*\))*\)\s*\{',
        re.MULTILINE
    )

    class_pattern = re.compile(r'\bclass\s+([a-zA-Z0-9_$]+)', re.MULTILINE)
    
    # Import pattern: import ... from ... or require(...)
    import_pattern = re.compile(r'\bimport\s+.*?\s+from\b|\brequire\s*\(', re.MULTILINE)

    # Find classes
    for match in class_pattern.finditer(code):
        result["classes"].append({"name": match.group(1), "has_docstring": False})

    # Find imports
    for match in import_pattern.finditer(code):
        result["imports"].append(match.group(0))

    # Find functions and count them
    for match in func_pattern.finditer(code):
        func_name = match.group(1) or match.group(2) or match.group(3)
        if func_name and func_name not in ("if", "for", "while", "switch", "catch"):
            result["functions"].append({
                "name": func_name,
                "complexity": 1,
            })

    # Complexity estimation: baseline 1 + count of keywords: if, for, while, catch, switch, case, &&, ||, ?
    complexity_keywords = re.compile(r'\b(if|for|while|catch|switch|case)\b|&&|\|\||\?')
    result["total_complexity"] = len(complexity_keywords.findall(code)) + 1

    return result


# ── Code-smell detection ─────────────────────────────────────

_MAGIC_NUMBER_RE = re.compile(r"(?<!=\s)(?<!\w)\b(?!0\b|1\b|2\b)(\d{2,})\b")


def find_code_smells(code: str, language: str) -> list[dict]:
    """Detect common code smells using heuristics.

    Currently supports Python and JS/TS at a deeper level; other
    languages fall back to line-based heuristics.

    Args:
        code: Source code string.
        language: Programming language name.

    Returns:
        List of smell dicts with keys ``type``, ``line``,
        ``description``, and ``severity``.
    """
    smells: list[dict] = []
    lines = code.splitlines()

    # ── Language-agnostic heuristics ─────────────────────────
    # Long file
    if len(lines) > 300:
        smells.append(
            {
                "type": "long_file",
                "line": 1,
                "description": f"File is {len(lines)} lines long (>300). Consider splitting.",
                "severity": "warning",
            }
        )

    # Magic numbers (rough)
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue
        matches = _MAGIC_NUMBER_RE.findall(stripped)
        for m in matches:
            smells.append(
                {
                    "type": "magic_number",
                    "line": idx,
                    "description": f"Magic number {m} — consider using a named constant.",
                    "severity": "info",
                }
            )

    # ── Python-specific smells via AST ───────────────────────
    if language.lower() == "python":
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return smells

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line = getattr(node, "end_lineno", node.lineno)
                func_len = end_line - node.lineno + 1
                # Long function
                if func_len > 50:
                    smells.append(
                        {
                            "type": "long_function",
                            "line": node.lineno,
                            "description": (
                                f"Function '{node.name}' is {func_len} lines "
                                f"long (>50). Consider breaking it up."
                            ),
                            "severity": "warning",
                        }
                    )
                # Missing docstring
                has_doc = (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(getattr(node.body[0], "value", None), ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )
                if not has_doc:
                    smells.append(
                        {
                            "type": "missing_docstring",
                            "line": node.lineno,
                            "description": f"Function '{node.name}' has no docstring.",
                            "severity": "info",
                        }
                    )

            # Deep nesting
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                depth = _max_nesting_depth(node)
                if depth > 4:
                    smells.append(
                        {
                            "type": "deep_nesting",
                            "line": node.lineno,
                            "description": (
                                f"Function '{node.name}' has nesting depth "
                                f"{depth} (>4). Refactor to reduce nesting."
                            ),
                            "severity": "warning",
                        }
                    )

    # ── JS/TS-specific smells ────────────────────────────────
    elif language.lower() in ("javascript", "typescript"):
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            if "console.log" in line:
                smells.append(
                    {
                        "type": "console_log",
                        "line": idx,
                        "description": "Uses 'console.log'. Consider using a proper logging library or deleting it.",
                        "severity": "info",
                    }
                )
            if re.search(r'\bvar\s+[a-zA-Z0-9_$]+', line):
                smells.append(
                    {
                        "type": "var_usage",
                        "line": idx,
                        "description": "Uses 'var' for variable declaration. Use 'let' or 'const' instead.",
                        "severity": "warning",
                    }
                )

    return smells


def get_file_metrics(code: str, language: str) -> dict[str, Any]:
    """Compute high-level metrics for a source file.

    Args:
        code: Source code string.
        language: Programming language name.

    Returns:
        Dict with keys ``lines_of_code``, ``function_count``,
        ``class_count``, ``import_count``, ``avg_function_length``,
        ``total_complexity``, ``code_smells``.
    """
    lines = code.splitlines()
    non_blank = [l for l in lines if l.strip()]

    metrics: dict[str, Any] = {
        "lines_of_code": len(lines),
        "non_blank_lines": len(non_blank),
        "function_count": 0,
        "class_count": 0,
        "import_count": 0,
        "avg_function_length": 0.0,
        "total_complexity": 0,
        "code_smells": [],
    }

    if language.lower() == "python":
        parsed = parse_python_file(code)
        metrics["function_count"] = len(parsed["functions"])
        metrics["class_count"] = len(parsed["classes"])
        metrics["import_count"] = len(parsed["imports"])
        metrics["total_complexity"] = parsed["total_complexity"]

        lengths = [f["length"] for f in parsed["functions"]]
        metrics["avg_function_length"] = (
            round(sum(lengths) / len(lengths), 1) if lengths else 0.0
        )
    elif language.lower() in ("javascript", "typescript"):
        parsed = parse_javascript_file(code)
        metrics["function_count"] = len(parsed["functions"])
        metrics["class_count"] = len(parsed["classes"])
        metrics["import_count"] = len(parsed["imports"])
        metrics["total_complexity"] = parsed["total_complexity"]

    # Code smells (works for all languages)
    metrics["code_smells"] = find_code_smells(code, language)

    return metrics
