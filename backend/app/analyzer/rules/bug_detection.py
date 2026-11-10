import ast
import difflib
import uuid
from typing import Dict, List, Set

from backend.app.schemas.analysis_schema import FindingSchema, SeverityEnum

class BugDetectionVisitor(ast.NodeVisitor):
    """
    AST NodeVisitor that detects static Python bugs and antipatterns:
    - BUG001: Mutable default arguments in function signatures
    - BUG002: Suspicious comparisons (== None, literal identity 'is', self-comparison)
    - BUG003: Suspicious exception handling (bare except, swallowed exception pass)
    - BUG004: Unreachable code following return, raise, break, continue
    - BUG005: Unused local variables in functions
    """

    def __init__(self, file_path: str, lines: List[str]):
        super().__init__()
        self.file_path = file_path
        self.lines = lines
        self.findings: List[FindingSchema] = []

    def _get_line_text(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1]
        return ""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_mutable_defaults(node)
        self._check_unreachable_code(node.body)
        self._check_unused_variables(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_mutable_defaults(node)
        self._check_unreachable_code(node.body)
        self._check_unused_variables(node)
        self.generic_visit(node)

    def _check_mutable_defaults(self, node: ast.AST):
        # 1. BUG001: Mutable default arguments
        args_obj = getattr(node, "args", None)
        if not args_obj:
            return

        all_defaults = args_obj.defaults + [d for d in args_obj.kw_defaults if d is not None]
        for default in all_defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                type_name = "list" if isinstance(default, ast.List) else ("dict" if isinstance(default, ast.Dict) else "set")
                line = default.lineno
                orig_line = self._get_line_text(line)
                snippet = orig_line.strip()

                diff_offset = len(args_obj.args) - len(args_obj.defaults)
                arg_name = "arg"
                for idx, d in enumerate(args_obj.defaults):
                    if d is default and (idx + diff_offset) < len(args_obj.args):
                        arg_name = args_obj.args[idx + diff_offset].arg
                        break

                indent = orig_line[:len(orig_line) - len(orig_line.lstrip())]
                corrected_line = orig_line.replace(f"{arg_name}=[]", f"{arg_name}=None")
                corrected_line = corrected_line.replace(f"{arg_name} = []", f"{arg_name}=None")
                corrected_line = corrected_line.replace(f"{arg_name}={{}}", f"{arg_name}=None")
                corrected_line = corrected_line.replace(f"{arg_name} = {{}}", f"{arg_name}=None")
                corrected_line = corrected_line.replace(f"{arg_name}=set()", f"{arg_name}=None")

                body_indent = indent + "    "
                init_statement = f"{body_indent}if {arg_name} is None: {arg_name} = []\n"

                diff = "".join(difflib.unified_diff(
                    [orig_line],
                    [corrected_line, init_statement],
                    fromfile=f"a/{self.file_path}",
                    tofile=f"b/{self.file_path}",
                    lineterm="\n"
                ))

                self.findings.append(FindingSchema(
                    id=f"bug-{uuid.uuid4().hex[:8]}",
                    rule_id="BUG001",
                    category="bug",
                    severity=SeverityEnum.ERROR,
                    title=f"Bug: Mutable Default Argument `{arg_name}`",
                    file_path=self.file_path,
                    line_number=line,
                    line=line,
                    column=default.col_offset + 1,
                    description=f"Function '{getattr(node, 'name', 'func')}' defines mutable default '{arg_name}={type_name}()'. State persists across calls.",
                    suggestion=f"Use '{arg_name}=None' in signature and initialize '{arg_name} = {type_name}()' inside body.",
                    suggested_fix=f"Use '{arg_name}=None' in signature and initialize '{arg_name} = {type_name}()' inside body.",
                    code_snippet=snippet,
                    explanation="Default argument values are evaluated once at definition time and shared across invocations.",
                    is_potential_warning=False,
                    fixable=True,
                    original_code=orig_line,
                    proposed_code=f"{corrected_line}{init_statement}",
                    unified_diff=diff
                ))

    def visit_Compare(self, node: ast.Compare):
        # 2. BUG002: Suspicious comparisons
        line = node.lineno
        orig_line = self._get_line_text(line)
        snippet = orig_line.strip()

        # Check comparison with None using == or !=
        for op, comp in zip(node.ops, node.comparators):
            is_none_comp = isinstance(comp, ast.Constant) and comp.value is None
            if is_none_comp:
                if isinstance(op, ast.Eq):
                    self.findings.append(FindingSchema(
                        id=f"bug-{uuid.uuid4().hex[:8]}",
                        rule_id="BUG002",
                        category="bug",
                        severity=SeverityEnum.WARNING,
                        title="Suspicious comparison: `== None` instead of `is None`",
                        file_path=self.file_path,
                        line_number=line,
                        line=line,
                        column=node.col_offset + 1,
                        description="Use `is None` rather than `== None` for testing identity against the None singleton.",
                        suggestion="Replace `== None` with `is None`.",
                        suggested_fix="Replace `== None` with `is None`.",
                        code_snippet=snippet,
                        explanation="In Python, identity comparison `is None` is faster and cannot be overridden by `__eq__` implementations.",
                        is_potential_warning=False,
                        fixable=True,
                        original_code=orig_line,
                        proposed_code=orig_line.replace("== None", "is None").replace("==None", "is None"),
                        unified_diff=""
                    ))
                elif isinstance(op, ast.NotEq):
                    self.findings.append(FindingSchema(
                        id=f"bug-{uuid.uuid4().hex[:8]}",
                        rule_id="BUG002",
                        category="bug",
                        severity=SeverityEnum.WARNING,
                        title="Suspicious comparison: `!= None` instead of `is not None`",
                        file_path=self.file_path,
                        line_number=line,
                        line=line,
                        column=node.col_offset + 1,
                        description="Use `is not None` rather than `!= None` for testing identity against the None singleton.",
                        suggestion="Replace `!= None` with `is not None`.",
                        suggested_fix="Replace `!= None` with `is not None`.",
                        code_snippet=snippet,
                        explanation="Singleton comparisons in Python should strictly use identity.",
                        is_potential_warning=False,
                        fixable=True,
                        original_code=orig_line,
                        proposed_code=orig_line.replace("!= None", "is not None").replace("!=None", "is not None"),
                        unified_diff=""
                    ))

            # Identity comparison with literals (e.g. x is "abc")
            if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(comp, ast.Constant) and comp.value is not None:
                if isinstance(comp.value, (str, int, float)):
                    self.findings.append(FindingSchema(
                        id=f"bug-{uuid.uuid4().hex[:8]}",
                        rule_id="BUG002",
                        category="bug",
                        severity=SeverityEnum.WARNING,
                        title="Suspicious literal comparison with 'is'",
                        file_path=self.file_path,
                        line_number=line,
                        line=line,
                        column=node.col_offset + 1,
                        description="Comparing literal values using 'is' tests object identity instead of value equality.",
                        suggestion="Use '==' or '!=' to compare literal strings, numbers, or floats.",
                        suggested_fix="Use '==' or '!=' to compare literal strings, numbers, or floats.",
                        code_snippet=snippet,
                        explanation="CPython intern pool optimizations mean 'is' on small literals may appear to work, but fails across platforms.",
                        is_potential_warning=False,
                        fixable=False,
                        original_code=orig_line,
                        proposed_code="",
                        unified_diff=""
                    ))

            # Self-comparison (x == x or x != x)
            if isinstance(node.left, ast.Name) and isinstance(comp, ast.Name):
                if node.left.id == comp.id:
                    self.findings.append(FindingSchema(
                        id=f"bug-{uuid.uuid4().hex[:8]}",
                        rule_id="BUG002",
                        category="bug",
                        severity=SeverityEnum.WARNING,
                        title=f"Suspicious self-comparison: `{node.left.id} == {comp.id}`",
                        file_path=self.file_path,
                        line_number=line,
                        line=line,
                        column=node.col_offset + 1,
                        description=f"Variable '{node.left.id}' is compared against itself, which is redundant or tautological.",
                        suggestion=f"Verify the comparison expression; self-comparison always evaluates to True or False.",
                        suggested_fix=f"Verify the comparison expression; self-comparison always evaluates to True or False.",
                        code_snippet=snippet,
                        explanation="Comparing an identifier to itself typically indicates a typo or copy-paste bug.",
                        is_potential_warning=False,
                        fixable=False,
                        original_code=orig_line,
                        proposed_code="",
                        unified_diff=""
                    ))

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # 3. BUG003: Suspicious exception handling
        line = node.lineno
        orig_line = self._get_line_text(line)
        snippet = orig_line.strip()

        # Bare except:
        if node.type is None:
            indent = orig_line[:len(orig_line) - len(orig_line.lstrip())]
            corrected_line = f"{indent}except Exception:\n"
            diff = "".join(difflib.unified_diff(
                [orig_line],
                [corrected_line],
                fromfile=f"a/{self.file_path}",
                tofile=f"b/{self.file_path}",
                lineterm="\n"
            ))

            self.findings.append(FindingSchema(
                id=f"bug-{uuid.uuid4().hex[:8]}",
                rule_id="BUG003",
                category="bug",
                severity=SeverityEnum.WARNING,
                title="Bug: Bare `except:` Catches BaseException",
                file_path=self.file_path,
                line_number=line,
                line=line,
                column=node.col_offset + 1,
                description="Bare `except:` catches `BaseException`, masking `KeyboardInterrupt` and `SystemExit`.",
                suggestion="Replace `except:` with `except Exception:` or specify the target exception type.",
                suggested_fix="Replace `except:` with `except Exception:` or specify the target exception type.",
                code_snippet=snippet,
                explanation="Bare except statements prevent proper program termination and complicate debugging.",
                is_potential_warning=False,
                fixable=True,
                original_code=orig_line,
                proposed_code=corrected_line,
                unified_diff=diff
            ))

        # Swallowed exception with bare pass
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            pass_line = node.body[0].lineno
            pass_snippet = self._get_line_text(pass_line).strip()
            self.findings.append(FindingSchema(
                id=f"bug-{uuid.uuid4().hex[:8]}",
                rule_id="BUG003",
                category="bug",
                severity=SeverityEnum.WARNING,
                title="Silent exception swallowing via bare 'pass'",
                file_path=self.file_path,
                line_number=pass_line,
                line=pass_line,
                column=node.body[0].col_offset + 1,
                description="Exception block catches error but suppresses it silently with a single 'pass' statement.",
                suggestion="Log the exception with logging.exception() or handle the error condition gracefully.",
                suggested_fix="Log the exception with logging.exception() or handle the error condition gracefully.",
                code_snippet=pass_snippet,
                explanation="Silently swallowing exceptions masks critical runtime failures and complicates debugging.",
                is_potential_warning=False,
                fixable=False,
                original_code=self._get_line_text(pass_line),
                proposed_code="",
                unified_diff=""
            ))

        self.generic_visit(node)

    def _check_unreachable_code(self, body: List[ast.stmt]):
        # 4. BUG004: Unreachable code detection
        terminating_types = (ast.Return, ast.Raise, ast.Break, ast.Continue)
        found_terminator = False
        for stmt in body:
            if found_terminator:
                line = stmt.lineno
                line_text = self._get_line_text(line)
                snippet = line_text.strip()
                self.findings.append(FindingSchema(
                    id=f"bug-{uuid.uuid4().hex[:8]}",
                    rule_id="BUG004",
                    category="bug",
                    severity=SeverityEnum.WARNING,
                    title="Unreachable code pattern detected",
                    file_path=self.file_path,
                    line_number=line,
                    line=line,
                    column=stmt.col_offset + 1,
                    description="Statement follows a terminal control-flow statement (return, raise, break, or continue) and will never execute.",
                    suggestion="Remove the dead code or correct the control flow.",
                    suggested_fix="Remove the dead code or correct the control flow.",
                    code_snippet=snippet,
                    explanation="Dead code after terminal statements confuses maintainers and indicates logic errors.",
                    is_potential_warning=False,
                    fixable=False,
                    original_code=line_text,
                    proposed_code="",
                    unified_diff=""
                ))
                break
            if isinstance(stmt, terminating_types):
                found_terminator = True

    def _check_unused_variables(self, node: ast.AST):
        # 5. BUG005: Unused local variables in function
        assigned_vars: Dict[str, int] = {}
        loaded_vars: Set[str] = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("_"):
                        assigned_vars.setdefault(target.id, child.lineno)
            elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                loaded_vars.add(child.id)

        for var_name, lineno in assigned_vars.items():
            if var_name not in loaded_vars:
                line_text = self._get_line_text(lineno)
                self.findings.append(FindingSchema(
                    id=f"bug-{uuid.uuid4().hex[:8]}",
                    rule_id="BUG005",
                    category="bug",
                    severity=SeverityEnum.INFORMATION,
                    title=f"Unused local variable: `{var_name}`",
                    file_path=self.file_path,
                    line_number=lineno,
                    line=lineno,
                    column=1,
                    description=f"Local variable '{var_name}' is assigned but never referenced or read in function.",
                    suggestion=f"Remove variable '{var_name}' or prefix with '_' if intentionally unused.",
                    suggested_fix=f"Remove variable '{var_name}' or prefix with '_' if intentionally unused.",
                    code_snippet=line_text.strip(),
                    explanation="Unused variables clutter code and may indicate missing computations or typos.",
                    is_potential_warning=False,
                    fixable=False,
                    original_code=line_text,
                    proposed_code="",
                    unified_diff=""
                ))

class BugDetector:
    """
    Backwards compatibility wrapper delegating to BugDetectionVisitor.
    """
    @classmethod
    def check_node(cls, node: ast.AST, file_path: str, lines: List[str]) -> List[FindingSchema]:
        visitor = BugDetectionVisitor(file_path=file_path, lines=lines)
        visitor.visit(node)
        return visitor.findings
