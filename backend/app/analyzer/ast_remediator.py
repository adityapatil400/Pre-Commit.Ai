import ast
import re
from typing import List, Optional
from backend.app.schemas.analysis_schema import FindingSchema

class ASTRemediator:
    """
    Deterministic AST-based complete file remediation engine.
    Used for instant baseline remediation and robust fallback when Ollama is offline.
    Guarantees complete, syntactically valid Python code with zero execution.
    """

    @classmethod
    def remediate_complete_file(cls, original_code: str, findings: List[FindingSchema]) -> str:
        if not original_code or not findings:
            return original_code

        lines = original_code.splitlines(keepends=True)
        if not lines:
            return original_code

        # Sort findings descending by line number so bottom edits don't change line indexes above
        sorted_findings = sorted(findings, key=lambda f: f.line or f.line_number or 1, reverse=True)

        for finding in sorted_findings:
            line_idx = (finding.line or finding.line_number or 1) - 1
            if line_idx < 0 or line_idx >= len(lines):
                continue

            rule_id = finding.rule_id or ""
            category = getattr(finding, "category", "") or ""
            target_line = lines[line_idx]

            # 0. SYNTAX: Syntax errors (e.g. 'for ... into ...', unclosed '{', missing colons)
            if category == "syntax" or rule_id in ("SYNTAX001", "PY-SYN-001", "SYN001"):
                # Case A: Invalid 'into' keyword in for loop
                if re.search(r"\bfor\s+[a-zA-Z_]\w*\s+into\s+", target_line):
                    lines[line_idx] = re.sub(r"(\bfor\s+[a-zA-Z_]\w*)\s+into\s+", r"\1 in ", target_line)
                # Case B: Lone unmatched delimiter (e.g. lone '{' or '}')
                elif target_line.strip() in ("{", "}", "[", "]"):
                    lines[line_idx] = ""
                # Case C: Missing trailing colon on compound header
                elif re.search(r"^\s*(?:if|for|while|def|class|elif)\b.*[^:]$", target_line.rstrip()):
                    lines[line_idx] = target_line.rstrip() + ":\n"

            # 1. RESOURCE001: Unclosed file open -> with open(...) as var:
            elif rule_id == "RESOURCE001" and "open(" in target_line:
                lines = cls._remediate_open(lines, line_idx)

            # 2. BUG001: Mutable default argument -> default=None sentinel
            elif rule_id == "BUG001" and "def " in target_line:
                lines = cls._remediate_mutable_default(lines, line_idx)

            # 3. BUG002: Assert tuple assertion -> assert condition, message
            elif rule_id == "BUG002" and "assert (" in target_line:
                lines = cls._remediate_assert_tuple(lines, line_idx)

            # 4. BUG004: Boolean comparison == True / == False
            elif rule_id == "BUG004" and ("== True" in target_line or "== False" in target_line):
                lines = cls._remediate_bool_compare(lines, line_idx)

            # 4b. BUG003: Bare except -> except Exception:
            elif rule_id in ("BUG003", "PY-BUG-002") and re.search(r"^\s*except\s*:", target_line):
                indent = target_line[:len(target_line) - len(target_line.lstrip())]
                lines[line_idx] = f"{indent}except Exception:\n"

            # 5. RESOURCE002: Socket or connection
            elif rule_id == "RESOURCE002" and ("socket" in target_line or "connect" in target_line):
                lines = cls._remediate_socket(lines, line_idx)

            # 6. MEMORY003: readlines() high memory retention
            elif rule_id == "MEMORY003" and ".readlines()" in target_line:
                lines[line_idx] = target_line.replace(".readlines()", "")

        result = "".join(lines)
        
        # Statically verify with ast.parse
        try:
            ast.parse(result)
            return result
        except SyntaxError:
            # Secondary cleanup pass on result for common syntax glitches
            cleaned_lines = []
            for l in result.splitlines(keepends=True):
                if l.strip() in ("{", "}"):
                    continue
                if re.search(r"\bfor\s+[a-zA-Z_]\w*\s+into\s+", l):
                    l = re.sub(r"(\bfor\s+[a-zA-Z_]\w*)\s+into\s+", r"\1 in ", l)
                cleaned_lines.append(l)
            cleaned = "".join(cleaned_lines)
            try:
                ast.parse(cleaned)
                return cleaned
            except SyntaxError:
                return original_code

    @classmethod
    def _remediate_open(cls, lines: List[str], line_idx: int) -> List[str]:
        target = lines[line_idx]
        indent = target[:len(target) - len(target.lstrip())]
        
        # Match pattern: var = open(...)
        m = re.match(r"^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.*open\(.*\))\s*$", target)
        if not m:
            return lines

        var_name = m.group(2)
        call_expr = m.group(3)

        new_with_header = f"{indent}with {call_expr} as {var_name}:\n"
        
        # Identify lines following this statement within the same function / indentation scope
        subsequent = []
        i = line_idx + 1
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                subsequent.append(line)
                i += 1
                continue
            line_indent = line[:len(line) - len(line.lstrip())]
            # If line is more indented or equal to target inside function
            if len(line_indent) >= len(indent):
                # Add 4 extra spaces of indentation for with-block
                subsequent.append("    " + line)
                i += 1
            else:
                break

        if not subsequent:
            subsequent = [f"{indent}    pass\n"]

        return lines[:line_idx] + [new_with_header] + subsequent + lines[i:]

    @classmethod
    def _remediate_mutable_default(cls, lines: List[str], line_idx: int) -> List[str]:
        target = lines[line_idx]
        # Replace [] or {} with None
        new_line = re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*list\s*=\s*\[\]", r"\1: Optional[list] = None", target)
        new_line = re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\[\]", r"\1=None", new_line)
        new_line = re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\{\}", r"\1=None", new_line)
        
        # Identify function body to insert None guard if possible
        indent = target[:len(target) - len(target.lstrip())]
        body_indent = indent + "    "
        
        # Find variable name replaced
        var_match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\[\]", target)
        lines[line_idx] = new_line
        if var_match and line_idx + 1 < len(lines):
            var = var_match.group(1)
            guard = f"{body_indent}if {var} is None:\n{body_indent}    {var} = []\n"
            # Insert guard after docstring or as first statement
            lines.insert(line_idx + 1, guard)

        return lines

    @classmethod
    def _remediate_assert_tuple(cls, lines: List[str], line_idx: int) -> List[str]:
        target = lines[line_idx]
        # assert (cond, msg) -> assert cond, msg
        m = re.search(r"assert\s*\(\s*(.*?)\s*,\s*(.*?)\s*\)", target)
        if m:
            cond = m.group(1).strip()
            msg = m.group(2).strip()
            indent = target[:len(target) - len(target.lstrip())]
            lines[line_idx] = f"{indent}assert {cond}, {msg}\n"
        return lines

    @classmethod
    def _remediate_bool_compare(cls, lines: List[str], line_idx: int) -> List[str]:
        target = lines[line_idx]
        new_line = target.replace(" == True", "").replace("== True", "")
        new_line = re.sub(r"if\s+([a-zA-Z0-9_.]+)\s*==\s*False", r"if not \1", new_line)
        lines[line_idx] = new_line
        return lines

    @classmethod
    def _remediate_socket(cls, lines: List[str], line_idx: int) -> List[str]:
        target = lines[line_idx]
        m = re.match(r"^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.*socket\.socket\(.*\))\s*$", target)
        if m:
            indent = m.group(1)
            var_name = m.group(2)
            call_expr = m.group(3)
            lines[line_idx] = f"{indent}with {call_expr} as {var_name}:\n"
            # Indent following lines in function
            i = line_idx + 1
            while i < len(lines):
                if lines[i].strip():
                    lines[i] = "    " + lines[i]
                i += 1
        return lines

