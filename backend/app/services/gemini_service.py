"""
Gemini AI service for SourceSage.

Demonstrates three core GenAI engineering patterns:
1. **Structured JSON output** — ``response_mime_type='application/json'``
   with a Pydantic-derived schema for type-safe responses.
2. **Tool / function calling** — registering tool declarations and
   processing the model's function-call requests in a loop.
3. **Prompt engineering** — rich system instructions with context
   injection (metrics, file tree, sample code).

Uses the **new** ``google-genai`` SDK (``google.genai``).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from app.config import settings
from app.models.schemas import CodeIssue, FileReview
from app.models.tools import ALL_TOOL_DECLARATIONS

logger = logging.getLogger(__name__)


class GeminiService:
    """Facade around the Google Gemini API for code analysis tasks.

    Args:
        api_key: Google API key. Falls back to ``settings.GOOGLE_API_KEY``.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.GOOGLE_API_KEY
        self._client = genai.Client(api_key=self._api_key)
        self._model = settings.MODEL_NAME

    # ── 1. Structured-output analysis ────────────────────────

    async def analyze_file(
        self,
        code: str,
        language: str,
        file_path: str,
        metrics: dict[str, Any],
    ) -> FileReview:
        """Analyse a single source file using structured JSON output.

        The Gemini model returns a JSON object that is validated
        directly into a :class:`FileReview` Pydantic model.

        Args:
            code: Source code of the file.
            language: Programming language name.
            file_path: Relative path of the file in the repository.
            metrics: Pre-computed static-analysis metrics dict.

        Returns:
            Validated :class:`FileReview` instance.
        """
        # Build the response schema matching FileReview
        response_schema = {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "language": {"type": "string"},
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "severity": {
                                "type": "string",
                                "enum": ["critical", "warning", "info"],
                            },
                            "category": {"type": "string"},
                            "file_path": {"type": "string"},
                            "line_number": {"type": "integer"},
                            "description": {"type": "string"},
                            "suggestion": {"type": "string"},
                            "code_snippet": {"type": "string"},
                        },
                        "required": [
                            "severity",
                            "category",
                            "file_path",
                            "description",
                            "suggestion",
                        ],
                    },
                },
                "score": {"type": "number"},
                "summary": {"type": "string"},
            },
            "required": ["file_path", "language", "issues", "score", "summary"],
        }

        prompt = self._build_analysis_prompt(code, language, file_path, metrics)

        try:
            response = await self._generate_async(
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.2,
                ),
            )

            raw_text = response.text
            data = json.loads(raw_text)

            # Ensure file_path is set correctly
            data["file_path"] = file_path
            data["language"] = language

            return FileReview.model_validate(data)

        except Exception as exc:
            logger.error("Gemini analysis failed for %s: %s", file_path, exc)
            # Return a fallback review so the pipeline doesn't break
            return FileReview(
                file_path=file_path,
                language=language,
                issues=[],
                score=50.0,
                summary=f"Analysis failed: {exc}",
            )

    # ── 2. Tool / function-calling analysis ──────────────────

    async def analyze_with_tools(
        self,
        code: str,
        language: str,
        file_path: str,
    ) -> list[CodeIssue]:
        """Analyse code using Gemini's function-calling (tool-use) pattern.

        The model is given tool declarations and may choose to call
        them.  We intercept those calls, execute them locally, and
        feed the results back until the model produces a final
        natural-language response.

        Args:
            code: Source code to analyse.
            language: Programming language.
            file_path: Relative path for context.

        Returns:
            List of :class:`CodeIssue` objects extracted from the
            conversation.
        """
        tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(**decl)
                    for decl in ALL_TOOL_DECLARATIONS
                ]
            )
        ]

        config = types.GenerateContentConfig(
            tools=tools,
            temperature=0.1,
        )

        prompt = (
            f"You are a senior code reviewer. Analyse the following {language} "
            f"file ({file_path}) for code quality, security vulnerabilities, "
            f"and refactoring opportunities.\n\n"
            f"Use the available tools to perform your analysis. Call each "
            f"relevant tool, then summarise all findings as a JSON array of "
            f"issues. Each issue must have: severity, category, file_path, "
            f"line_number (nullable), description, suggestion, code_snippet (nullable).\n\n"
            f"```{language}\n{code}\n```"
        )

        issues: list[CodeIssue] = []

        try:
            # Initial request
            response = await self._generate_async(
                contents=prompt,
                config=config,
            )

            # Process tool calls in a loop (multi-turn)
            conversation_history: list[types.Content] = [
                types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
            ]
            max_iterations = 5
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Check if the response has function calls
                if not response.candidates or not response.candidates[0].content.parts:
                    break

                has_function_call = False
                function_response_parts: list[types.Part] = []

                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        has_function_call = True
                        fn_name = part.function_call.name
                        fn_args = dict(part.function_call.args) if part.function_call.args else {}

                        logger.info(
                            "Tool call: %s(%s)", fn_name, list(fn_args.keys())
                        )

                        # Execute the tool locally
                        tool_result = self._execute_tool(fn_name, fn_args)

                        function_response_parts.append(
                            types.Part.from_function_response(
                                name=fn_name,
                                response={"result": tool_result},
                            )
                        )

                if not has_function_call:
                    # Model produced a final text response — parse issues
                    final_text = response.text or ""
                    issues = self._parse_issues_from_text(final_text, file_path)
                    break

                # Add model's response and our tool results to history
                conversation_history.append(response.candidates[0].content)
                conversation_history.append(
                    types.Content(role="user", parts=function_response_parts)
                )

                # Send tool results back to the model
                response = await self._generate_async(
                    contents=conversation_history,
                    config=config,
                )

            # After the loop, if we still haven't parsed issues
            if not issues and response.text:
                issues = self._parse_issues_from_text(response.text, file_path)

        except Exception as exc:
            logger.error("Tool-based analysis failed for %s: %s", file_path, exc)

        return issues

    # ── 3. Documentation generation ──────────────────────────

    async def generate_documentation(
        self,
        code: str,
        language: str,
        file_path: str,
    ) -> str:
        """Generate comprehensive documentation for a source file.

        Args:
            code: Source code string.
            language: Programming language.
            file_path: Relative file path.

        Returns:
            Markdown-formatted documentation string.
        """
        prompt = (
            f"Generate comprehensive documentation for the following "
            f"{language} file ({file_path}).\n\n"
            f"Include:\n"
            f"- Module overview\n"
            f"- Description of each function / class and its parameters\n"
            f"- Usage examples where helpful\n"
            f"- Return value descriptions\n"
            f"- Any important notes or caveats\n\n"
            f"Format the output as clean Markdown.\n\n"
            f"```{language}\n{code}\n```"
        )

        response_schema = {
            "type": "object",
            "properties": {
                "documentation": {
                    "type": "string",
                    "description": "Complete Markdown documentation for the file.",
                },
            },
            "required": ["documentation"],
        }

        try:
            response = await self._generate_async(
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.3,
                ),
            )
            data = json.loads(response.text)
            return data.get("documentation", response.text)
        except Exception as exc:
            logger.error("Doc generation failed for %s: %s", file_path, exc)
            return f"_Documentation generation failed: {exc}_"

    async def generate_readme(
        self,
        file_tree: list[dict],
        sample_code: dict[str, str],
    ) -> str:
        """Generate a README.md from the repository structure and samples.

        Args:
            file_tree: List of file-info dicts (path, size, language).
            sample_code: Mapping of select file paths to their content.

        Returns:
            Markdown README content.
        """
        tree_summary = "\n".join(
            f"- {f['path']} ({f['language']}, {f['size']} bytes)"
            for f in file_tree[:50]  # cap for context window
        )

        samples_section = ""
        for path, code in list(sample_code.items())[:5]:
            samples_section += f"\n### {path}\n```\n{code[:500]}\n```\n"

        prompt = (
            f"Generate a professional README.md for a repository with the "
            f"following structure:\n\n{tree_summary}\n\n"
            f"Sample file contents:\n{samples_section}\n\n"
            f"Include these sections:\n"
            f"- Project title and description\n"
            f"- Features\n"
            f"- Installation instructions\n"
            f"- Usage / Quick start\n"
            f"- Project structure\n"
            f"- Contributing guidelines\n"
            f"- License placeholder\n"
        )

        try:
            response = await self._generate_async(
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.4),
            )
            return response.text or ""
        except Exception as exc:
            logger.error("README generation failed: %s", exc)
            return f"# README\n\n_Generation failed: {exc}_"

    # ── Private helpers ──────────────────────────────────────

    async def _generate_async(
        self,
        contents: Any,
        config: types.GenerateContentConfig | None = None,
    ) -> Any:
        """Wrapper around the asynchronous Gemini client.

        Uses the native ``client.aio`` interface from the ``google-genai`` SDK.
        """
        return await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )

    @staticmethod
    def _build_analysis_prompt(
        code: str,
        language: str,
        file_path: str,
        metrics: dict[str, Any],
    ) -> str:
        """Build a rich prompt for structured code analysis."""
        metrics_str = "\n".join(f"  - {k}: {v}" for k, v in metrics.items() if k != "code_smells")
        smells = metrics.get("code_smells", [])
        smells_str = (
            "\n".join(f"  - [{s['severity']}] L{s['line']}: {s['description']}" for s in smells)
            if smells
            else "  (none detected)"
        )

        return (
            f"You are SourceSage, a senior code reviewer AI.  Analyse the "
            f"following {language} file and return a structured review.\n\n"
            f"## File: {file_path}\n\n"
            f"### Pre-computed Metrics\n{metrics_str}\n\n"
            f"### Static Code Smells\n{smells_str}\n\n"
            f"### Source Code\n```{language}\n{code}\n```\n\n"
            f"Evaluate:\n"
            f"1. Code quality and readability\n"
            f"2. Potential bugs and edge cases\n"
            f"3. Security vulnerabilities\n"
            f"4. Performance concerns\n"
            f"5. Best-practice adherence\n\n"
            f"Return your review as the specified JSON schema. "
            f"Score 0-100 (100 = perfect). Be specific in suggestions."
        )

    @staticmethod
    def _execute_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call locally and return the result.

        Performs real, lightweight code analysis and structural checks.
        """
        result: dict[str, Any] = {"tool": name, "status": "executed"}

        if name == "analyze_code_quality":
            code = args.get("code", "")
            lines = code.splitlines()
            issues_found = []
            
            # Simple heuristic checks
            for idx, line in enumerate(lines, start=1):
                if len(line) > 120:
                    issues_found.append(f"Line {idx} exceeds 120 characters ({len(line)} chars).")
                if "TODO" in line or "FIXME" in line:
                    issues_found.append(f"Line {idx} contains developer comment placeholder (TODO/FIXME).")
            
            result["analysis"] = {
                "file_path": args.get("file_path", "unknown"),
                "language": args.get("language", "unknown"),
                "line_count": len(lines),
                "issues_detected": issues_found or ["No simple code smells detected."],
                "has_docstrings": '"""' in code or "'''" in code or "/**" in code or "/*" in code,
            }
        elif name == "detect_security_vulnerability":
            code = args.get("code", "")
            vulns = []
            
            # Heuristic regex patterns for common security vulnerabilities
            patterns = {
                "hardcoded_secret": r"(?i)(password|secret|passwd|api_key|apikey|private_key|token)\s*=\s*['\"][a-zA-Z0-9_\-\+]{10,}['\"]",
                "unsafe_execution": r"\b(eval|exec|subprocess\.Popen\(.*?shell\s*=\s*True|child_process\.exec)\b",
                "sql_injection": r"(?i)(SELECT|INSERT|UPDATE|DELETE).*?\+.*?\b",
                "insecure_deserialization": r"\b(pickle\.loads|yaml\.load)\b",
            }
            
            import re
            for key, pattern in patterns.items():
                for match in re.finditer(pattern, code):
                    line_num = code[:match.start()].count("\n") + 1
                    vulns.append({
                        "type": key,
                        "line": line_num,
                        "match": match.group(0)[:50],
                        "description": f"Potential {key.replace('_', ' ')} vulnerability detected."
                    })
                    
            result["analysis"] = {
                "vulnerabilities_found": vulns,
                "scan_status": "Success",
                "rules_scanned": list(patterns.keys())
            }
        elif name == "generate_docstring":
            code = args.get("code", "")
            el_type = args.get("element_type", "function")
            import re
            
            # Extract name and params
            name_match = re.search(r'\b(def|class|function)\s+([a-zA-Z0-9_$]+)', code)
            name = name_match.group(2) if name_match else "element"
            
            params = []
            if el_type == "function":
                param_match = re.search(r'\((.*?)\)', code)
                if param_match:
                    params = [p.strip().split(':')[0].split('=')[0].strip() for p in param_match.group(1).split(',') if p.strip()]
            
            # Build standard docstring template
            if el_type == "class":
                docstring = f'"""Class {name}.\n\nDetailed class description goes here.\n"""'
            elif el_type == "module":
                docstring = f'"""Module {name}.\n\nModule level documentation goes here.\n"""'
            else:
                param_section = "\n    Args:\n" + "\n".join(f"        {p}: Description of {p}." for p in params) if params else ""
                docstring = f'"""Function {name}.\n\nDetailed function description goes here.{param_section}\n\n    Returns:\n        Description of return value.\n    """'
                
            result["docstring"] = docstring
        elif name == "suggest_refactoring":
            code = args.get("code", "")
            complexity = args.get("complexity_score", 1)
            suggestions = []
            
            lines = code.splitlines()
            if len(lines) > 50:
                suggestions.append("Break the block into smaller functions to improve readability.")
            if complexity > 5:
                suggestions.append("Simplify control flow (e.g. reduce nested if/for/while blocks).")
            if any(line.startswith(" " * 16) for line in lines):
                suggestions.append("Deep indentation levels detected. Extract nested logic into separate helper methods.")
                
            result["suggestions"] = suggestions or ["Structure is clean. Standard formatting applied."]
        else:
            result["error"] = f"Unknown tool: {name}"

        return result

    @staticmethod
    def _parse_issues_from_text(text: str, file_path: str) -> list[CodeIssue]:
        """Best-effort extraction of issues from a free-text response.

        Tries to parse a JSON array from the response; falls back
        to an empty list if the text is not valid JSON.
        """
        try:
            # Try to find a JSON array in the text
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1:
                raw = json.loads(text[start : end + 1])
                issues: list[CodeIssue] = []
                for item in raw:
                    item.setdefault("file_path", file_path)
                    item.setdefault("severity", "info")
                    item.setdefault("category", "general")
                    item.setdefault("description", "")
                    item.setdefault("suggestion", "")
                    issues.append(CodeIssue.model_validate(item))
                return issues
        except (json.JSONDecodeError, Exception) as exc:
            logger.debug("Could not parse issues from text: %s", exc)

        return []
