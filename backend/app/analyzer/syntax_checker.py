import ast
import io
import re
import tokenize
import uuid
from typing import Dict, List, Optional

from backend.app.schemas.analysis_schema import FindingSchema, SeverityEnum, CategoryEnum
from backend.app.schemas.syntax_schema import SyntaxErrorDetail
from backend.app.utils.logger import logger

class SyntaxChecker:
    """
    Analyzes, classifies, and formats syntax errors and indentation failures
    encountered during Python AST parsing.
    
    Provides multi-pass syntax detection:
    - Pass 1: Tokenizer Delimiter & Syntax Pattern Scanner (catches unclosed braces/brackets/quotes, 'into' loops).
    - Pass 2: Smart Iterative AST Masking Loop (re-parses with neutral masks to discover downstream errors).
    - Pass 3: Top-level block chunk verification (verifies individual statements/blocks independently).
    """

    @classmethod
    def classify_syntax_error(cls, exc: SyntaxError) -> str:
        """
        Classifies Python parser errors into specific error types:
        - IndentationError
        - TabError
        - UnexpectedEOFError
        - UnmatchedBracketError
        - EncodingError
        - SyntaxError
        """
        msg = (exc.msg or "").lower()

        if isinstance(exc, TabError):
            return "TabError"
        if isinstance(exc, IndentationError):
            return "IndentationError"

        if "unexpected eof" in msg or "unexpected end of file" in msg:
            return "UnexpectedEOFError"

        if (
            "was never closed" in msg
            or "closing parenthesis" in msg
            or "unmatched" in msg
            or "does not match opening parenthesis" in msg
        ):
            return "UnmatchedBracketError"

        if "encoding error" in msg or "codec can't decode" in msg or "null byte" in msg:
            return "EncodingError"

        return "SyntaxError"

    @classmethod
    def format_error_detail(
        cls,
        exc: SyntaxError,
        file_path: str,
        source_code: str = ""
    ) -> SyntaxErrorDetail:
        """
        Constructs a structured SyntaxErrorDetail object with location and snippet info.
        """
        line = exc.lineno or 1
        col = exc.offset or 1
        msg = exc.msg or "Invalid Python syntax"
        error_type = cls.classify_syntax_error(exc)

        # Extract source code snippet
        snippet = ""
        if exc.text:
            snippet = exc.text.strip()
        elif source_code:
            lines = source_code.splitlines()
            if 1 <= line <= len(lines):
                snippet = lines[line - 1].strip()

        suggestion = f"Correct syntax around line {line}: {msg}"
        msg_lower = msg.lower()
        if "expected ':'" in msg_lower or ":" in msg_lower:
            suggestion = "Ensure statement has a trailing colon ':' and proper block indentation."
        elif "unmatched" in msg_lower or "was never closed" in msg_lower:
            suggestion = "Ensure all parentheses '()', brackets '[]', and braces '{}' are properly closed."
        elif isinstance(exc, IndentationError):
            suggestion = "Ensure consistent indentation (prefer 4 spaces) and matching block levels."
        elif re.search(r"\bfor\s+\w+\s+into\b", snippet):
            msg = "Invalid keyword 'into' in for loop."
            suggestion = "Replace 'into' with 'in'."

        return SyntaxErrorDetail(
            file_path=file_path,
            line_number=line,
            column_number=col,
            error_type=error_type,
            error_message=msg,
            source_snippet=snippet,
            suggestion=suggestion,
        )

    @classmethod
    def format_syntax_error(
        cls,
        exc: SyntaxError,
        file_path: str,
        source_code: str
    ) -> FindingSchema:
        """
        Formats a SyntaxError into a FindingSchema for full static analysis reports.
        Preserves backwards compatibility with AnalysisEngine.
        """
        detail = cls.format_error_detail(exc, file_path, source_code)
        line = detail.line_number
        msg = detail.error_message
        snippet = detail.source_snippet
        suggested = detail.suggestion

        return FindingSchema(
            id=f"syn-{uuid.uuid4().hex[:8]}",
            rule_id="PY-SYN-001",
            title=f"{detail.error_type}: {msg}",
            severity=SeverityEnum.ERROR,
            category=CategoryEnum.SYNTAX.value,
            file_path=file_path,
            line=line,
            line_number=line,
            column=detail.column_number,
            end_line=getattr(exc, "end_lineno", line),
            end_column=getattr(exc, "end_offset", detail.column_number),
            description=f"Python syntax compilation failure on line {line}: {msg}.",
            code_snippet=snippet,
            problematic_code=snippet,
            message=msg,
            suggestion=suggested,
            suggested_fix=suggested,
            explanation="Definitive AST compilation error. The Python interpreter cannot compile or import this file.",
            is_potential_warning=False,
            fixable=True,
            original_code=source_code or snippet,
            proposed_code="",
            unified_diff=""
        )

    @classmethod
    def check_multiple_syntax_errors(
        cls,
        source_code: str,
        file_path: str = "snippet.py"
    ) -> List[SyntaxErrorDetail]:
        """
        Discovers ALL syntax errors in a single Python file using a multi-pass approach:
        1. Tokenizer scanning for delimiter balance, unexpected EOF, and invalid keywords (e.g. 'for ... into ...').
        2. Iterative AST parsing with progressive masking to uncover downstream syntax errors.
        3. Block-level parsing to verify statements independently.
        4. Deduplicates and orders findings by (line_number, column_number).
        """
        if not source_code or not source_code.strip():
            return []

        lines = source_code.splitlines(keepends=True)
        detected: Dict[int, SyntaxErrorDetail] = {}

        def record_error(
            line: int,
            col: int,
            err_type: str,
            msg: str,
            snippet: str,
            suggestion: str
        ) -> None:
            if line not in detected:
                detected[line] = SyntaxErrorDetail(
                    file_path=file_path,
                    line_number=line,
                    column_number=col,
                    error_type=err_type,
                    error_message=msg,
                    source_snippet=snippet,
                    suggestion=suggestion,
                )
            else:
                curr = detected[line]
                # Upgrade if current error is generic and new is more specific
                if curr.error_type == "SyntaxError" and err_type != "SyntaxError":
                    curr.error_type = err_type
                    curr.error_message = msg
                    curr.suggestion = suggestion
                elif "invalid syntax" in curr.error_message.lower() and "invalid syntax" not in msg.lower():
                    curr.error_message = msg
                    curr.suggestion = suggestion

        # -------------------------------------------------------------------
        # Pass 1: Tokenizer Delimiter & Pattern Scanner
        # -------------------------------------------------------------------
        stack: List[tuple] = []
        delims = {"(": ")", "[": "]", "{": "}"}
        open_delims = set(delims.keys())
        close_delims = {v: k for k, v in delims.items()}

        prev_tok = None
        prev_prev_tok = None

        try:
            token_gen = tokenize.tokenize(io.BytesIO(source_code.encode("utf-8")).readline)
            for t in token_gen:
                # Delimiter tracking
                if t.exact_type in (tokenize.LPAR, tokenize.LSQB, tokenize.LBRACE) or t.string in open_delims:
                    stack.append((t.string, t.start[0], t.start[1]))
                elif t.exact_type in (tokenize.RPAR, tokenize.RSQB, tokenize.RBRACE) or t.string in close_delims:
                    if stack and stack[-1][0] == close_delims.get(t.string):
                        stack.pop()
                    elif stack:
                        opening, o_line, _ = stack.pop()
                        line_text = lines[t.start[0] - 1].strip() if t.start[0] <= len(lines) else ""
                        record_error(
                            t.start[0],
                            t.start[1],
                            "UnmatchedBracketError",
                            f"Closing '{t.string}' does not match opening '{opening}' at line {o_line}.",
                            line_text,
                            f"Ensure '{opening}' and '{t.string}' match and are balanced."
                        )
                    else:
                        line_text = lines[t.start[0] - 1].strip() if t.start[0] <= len(lines) else ""
                        record_error(
                            t.start[0],
                            t.start[1],
                            "UnmatchedBracketError",
                            f"Unmatched closing '{t.string}' without matching opening delimiter.",
                            line_text,
                            f"Remove or balance unmatched '{t.string}'."
                        )

                # Invalid loop keyword pattern: for <var> into <expr>:
                if t.type == tokenize.NAME and t.string == "into":
                    if prev_tok and prev_tok.type == tokenize.NAME and prev_prev_tok and prev_prev_tok.string == "for":
                        line_text = lines[t.start[0] - 1].strip() if t.start[0] <= len(lines) else ""
                        record_error(
                            t.start[0],
                            t.start[1] + 1,
                            "SyntaxError",
                            "Invalid keyword 'into' in for loop.",
                            line_text,
                            "Replace 'into' with 'in'."
                        )

                # Invalid keywords commonly imported from other languages
                elif t.type == tokenize.NAME:
                    line_text = lines[t.start[0] - 1].strip() if t.start[0] <= len(lines) else ""
                    if t.string in ("elsif", "elseif"):
                        record_error(t.start[0], t.start[1] + 1, "SyntaxError", f"Invalid keyword '{t.string}'.", line_text, "Replace with 'elif'.")
                    elif t.string == "function" and prev_tok and prev_tok.string not in (".", "import", "from"):
                        record_error(t.start[0], t.start[1] + 1, "SyntaxError", "Invalid keyword 'function'.", line_text, "Replace with 'def'.")
                    elif t.string == "null":
                        record_error(t.start[0], t.start[1] + 1, "SyntaxError", "Invalid identifier 'null'.", line_text, "Use 'None' in Python.")

                if t.type not in (tokenize.COMMENT, tokenize.NL, tokenize.ENCODING):
                    prev_prev_tok = prev_tok
                    prev_tok = t
        except tokenize.TokenError as te:
            logger.debug(f"Tokenizer error in {file_path}: {te}")
        except Exception as e:
            logger.debug(f"Tokenizer pass exception in {file_path}: {e}")

        # Unmatched opening delimiters remaining in stack
        for opening, o_line, o_col in stack:
            delim_name = {"{": "opening curly brace", "[": "opening bracket", "(": "opening parenthesis"}.get(opening, "delimiter")
            close_ch = delims.get(opening, "")
            line_text = lines[o_line - 1].strip() if o_line <= len(lines) else opening
            record_error(
                o_line,
                o_col + 1,
                "UnmatchedBracketError",
                f"Unexpected unmatched {delim_name} '{opening}' was never closed.",
                line_text,
                f"Remove the unnecessary {delim_name} '{opening}' or close it with '{close_ch}'."
            )

        # -------------------------------------------------------------------
        # Pass 2: Iterative AST Parse with Smart Masking
        # -------------------------------------------------------------------
        working_lines = list(lines)
        # Pre-mask lone unclosed delimiters from Pass 1 to prevent false cascade
        for opening, o_line, _ in stack:
            if 1 <= o_line <= len(working_lines):
                cur_text = working_lines[o_line - 1].strip()
                if cur_text in ("{", "}", "[", "]", "(", ")"):
                    indent = working_lines[o_line - 1][:len(working_lines[o_line - 1]) - len(working_lines[o_line - 1].lstrip())]
                    working_lines[o_line - 1] = f"{indent}# masked delimiter\n"

        max_passes = min(len(lines) + 10, 50)
        for _ in range(max_passes):
            working_src = "".join(working_lines)
            try:
                ast.parse(working_src, filename=file_path)
                break
            except (SyntaxError, IndentationError) as exc:
                err_line = exc.lineno or 1
                err_col = exc.offset or 1
                err_msg = exc.msg or "Invalid syntax"
                err_text = lines[err_line - 1].strip() if 1 <= err_line <= len(lines) else (exc.text or "").strip()

                err_type = cls.classify_syntax_error(exc)
                suggestion = "Correct syntax error on this line."
                if isinstance(exc, IndentationError):
                    err_type = "IndentationError"
                    suggestion = "Ensure consistent 4-space indentation and matching block levels."
                elif "expected ':'" in err_msg.lower():
                    suggestion = "Add trailing colon ':' to statement header."
                elif "was never closed" in err_msg.lower() or "unmatched" in err_msg.lower():
                    err_type = "UnmatchedBracketError"
                    suggestion = "Ensure all brackets, braces, and parentheses are closed."
                elif re.search(r"\bfor\s+\w+\s+into\b", err_text):
                    err_msg = "Invalid keyword 'into' in for loop."
                    suggestion = "Replace 'into' with 'in'."

                record_error(err_line, err_col, err_type, err_msg, err_text, suggestion)

                # Mask problematic line in working lines to uncover downstream syntax errors
                if 1 <= err_line <= len(working_lines):
                    cur = working_lines[err_line - 1]
                    indent = cur[:len(cur) - len(cur.lstrip())]
                    stripped = cur.strip()

                    if stripped.startswith(("for ", "while ", "if ", "elif ", "else:", "try:", "except", "with ", "def ", "class ")):
                        working_lines[err_line - 1] = f"{indent}if True:\n"
                    elif stripped in ("{", "}", "[", "]", "(", ")"):
                        working_lines[err_line - 1] = f"{indent}# masked\n"
                    else:
                        next_indent = ""
                        if err_line < len(working_lines):
                            next_indent = working_lines[err_line][:len(working_lines[err_line]) - len(working_lines[err_line].lstrip())]
                        if len(next_indent) > len(indent):
                            working_lines[err_line - 1] = f"{indent}if True:\n"
                        else:
                            working_lines[err_line - 1] = f"{indent}pass\n"
                else:
                    break

        # -------------------------------------------------------------------
        # Pass 3: Top-Level Statement Block Verification
        # -------------------------------------------------------------------
        top_blocks: List[tuple] = []
        cur_block: List[str] = []
        cur_start = 1
        for i, line in enumerate(lines, 1):
            if line.strip() and not line.startswith((" ", "\t", "#")) and cur_block:
                top_blocks.append((cur_start, cur_block))
                cur_block = [line]
                cur_start = i
            else:
                cur_block.append(line)
        if cur_block:
            top_blocks.append((cur_start, cur_block))

        for start_line, block_lines in top_blocks:
            block_src = "".join(block_lines)
            if not block_src.strip():
                continue
            try:
                ast.parse(block_src)
            except (SyntaxError, IndentationError) as exc:
                actual_line = start_line + (exc.lineno or 1) - 1
                col = exc.offset or 1
                msg = exc.msg or "Invalid syntax"
                snip = lines[actual_line - 1].strip() if 1 <= actual_line <= len(lines) else ""
                sugg = "Correct syntax error in this statement block."
                if re.search(r"\bfor\s+\w+\s+into\b", snip):
                    msg = "Invalid keyword 'into' in for loop."
                    sugg = "Replace 'into' with 'in'."
                record_error(
                    actual_line,
                    col,
                    cls.classify_syntax_error(exc) if not isinstance(exc, IndentationError) else "IndentationError",
                    msg,
                    snip,
                    sugg
                )

        # Sort errors chronologically by line and column
        result = list(detected.values())
        result.sort(key=lambda x: (x.line_number, x.column_number))
        return result

    @classmethod
    def format_all_syntax_errors(
        cls,
        source_code: str,
        file_path: str
    ) -> List[FindingSchema]:
        """
        Detects and formats all syntax errors in a source file into a list of FindingSchema.
        """
        details = cls.check_multiple_syntax_errors(source_code, file_path)
        findings: List[FindingSchema] = []

        for detail in details:
            findings.append(FindingSchema(
                id=f"syn-{uuid.uuid4().hex[:8]}",
                rule_id="SYNTAX001",
                title=f"{detail.error_type}: {detail.error_message}",
                severity=SeverityEnum.ERROR,
                category=CategoryEnum.SYNTAX.value,
                file_path=file_path,
                line=detail.line_number,
                line_number=detail.line_number,
                column=detail.column_number,
                description=f"Python syntax compilation error on line {detail.line_number}: {detail.error_message}.",
                code_snippet=detail.source_snippet,
                problematic_code=detail.source_snippet,
                message=detail.error_message,
                suggestion=detail.suggestion or "Correct the syntax error.",
                suggested_fix=detail.suggestion or "Correct the syntax error.",
                explanation="Definitive AST compilation failure. Python cannot compile this file.",
                is_potential_warning=False,
                fixable=True,
                original_code=source_code,
                proposed_code="",
                unified_diff=""
            ))

        return findings
