"""
Gemini function-calling tool declarations for SourceSage.

Each dict follows the OpenAPI-style schema expected by
`google.genai.types.FunctionDeclaration`.  These are registered
with the Gemini model so it can invoke structured analysis tools.
"""

# ── Tool: Code Quality Analysis ──────────────────────────────

ANALYZE_CODE_QUALITY = {
    "name": "analyze_code_quality",
    "description": (
        "Analyse the given source code for quality issues including "
        "code smells, anti-patterns, naming conventions, and best-practice "
        "violations.  Return a structured list of issues."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The full source code to analyse.",
            },
            "language": {
                "type": "string",
                "description": "Programming language of the code (e.g. 'python').",
            },
            "file_path": {
                "type": "string",
                "description": "Relative file path for context.",
            },
        },
        "required": ["code", "language", "file_path"],
    },
}

# ── Tool: Security Vulnerability Detection ───────────────────

DETECT_SECURITY_VULNERABILITY = {
    "name": "detect_security_vulnerability",
    "description": (
        "Scan the provided source code for security vulnerabilities such as "
        "SQL injection, XSS, hardcoded secrets, insecure deserialization, "
        "and other OWASP Top-10 issues."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Source code to scan.",
            },
            "language": {
                "type": "string",
                "description": "Programming language of the code.",
            },
        },
        "required": ["code", "language"],
    },
}

# ── Tool: Docstring Generation ───────────────────────────────

GENERATE_DOCSTRING = {
    "name": "generate_docstring",
    "description": (
        "Generate a comprehensive docstring for the given code element "
        "(function, class, or module).  Follow the language's standard "
        "documentation conventions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Source code of the element to document.",
            },
            "language": {
                "type": "string",
                "description": "Programming language of the code.",
            },
            "element_type": {
                "type": "string",
                "description": "Type of element: 'function', 'class', or 'module'.",
                "enum": ["function", "class", "module"],
            },
        },
        "required": ["code", "language", "element_type"],
    },
}

# ── Tool: Refactoring Suggestions ────────────────────────────

SUGGEST_REFACTORING = {
    "name": "suggest_refactoring",
    "description": (
        "Suggest concrete refactoring improvements for the given code "
        "based on its complexity score and structure.  Focus on reducing "
        "cognitive complexity, improving readability, and applying SOLID "
        "principles."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Source code to refactor.",
            },
            "language": {
                "type": "string",
                "description": "Programming language of the code.",
            },
            "complexity_score": {
                "type": "number",
                "description": "Cyclomatic / cognitive complexity score of the code.",
            },
        },
        "required": ["code", "language", "complexity_score"],
    },
}

# ── Convenience list of all declarations ─────────────────────

ALL_TOOL_DECLARATIONS: list[dict] = [
    ANALYZE_CODE_QUALITY,
    DETECT_SECURITY_VULNERABILITY,
    GENERATE_DOCSTRING,
    SUGGEST_REFACTORING,
]
