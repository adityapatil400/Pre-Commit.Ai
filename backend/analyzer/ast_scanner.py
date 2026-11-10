import ast
import difflib
import uuid
from typing import List, Dict, Optional, Tuple, Set
from .models import Finding

class ASTScanner:
    """
    Python AST-Based Static Code Analysis Scanner.
    Strictly inspects Python AST without executing any user code.
    """

    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.lines = source_code.splitlines(keepends=True)
        self.findings: List[Finding] = []
        self._global_collections: Set[str] = set()

    def scan(self) -> List[Finding]:
        self.findings.clear()

        # Step 1: Check for syntax errors by parsing AST
        try:
            tree = ast.parse(self.source_code, filename=self.file_path)
        except SyntaxError as e:
            line = e.lineno or 1
            col = e.offset or 1
            snippet = e.text.strip() if e.text else (self.lines[line - 1].strip() if line <= len(self.lines) else "")
            
            suggested = f"Fix syntax error at line {line}: {e.msg}"
            if "expected ':'" in str(e).lower() or ":" in str(e).lower():
                suggested = "Ensure statement has a trailing colon ':' and proper indentation."
            elif "unmatched" in str(e).lower() or "was never closed" in str(e).lower():
                suggested = "Ensure all parentheses '()', brackets '[]', and braces '{}' are properly closed."

            self.findings.append(Finding(
                id=f"f-{uuid.uuid4().hex[:8]}",
                rule_id="PY-SYN-001",
                title=f"SyntaxError: {e.msg}",
                severity="error",
                category="syntax",
                file_path=self.file_path,
                line=line,
                column=col,
                end_line=getattr(e, "end_lineno", line),
                end_column=getattr(e, "end_offset", col),
                description=f"Python parser error: {e.msg} on line {line}.",
                code_snippet=snippet,
                suggested_fix=suggested,
                explanation="Definitive AST compilation error. Python code cannot be compiled or imported while containing syntax errors.",
                is_potential_warning=False,
                fixable=False,
                original_code=snippet,
                proposed_code="",
                unified_diff="",
            ))
            return self.findings

        # Step 2: AST Node Analysis
        self._find_module_level_collections(tree)
        self._analyze_ast(tree)
        return self.findings

    def _find_module_level_collections(self, tree: ast.AST):
        """Identify module-level mutable containers for memory leak heuristics."""
        for stmt in getattr(tree, "body", []):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(stmt.value, (ast.List, ast.Dict, ast.Set)):
                            self._global_collections.add(target.id)

    def _analyze_ast(self, tree: ast.AST):
        for node in ast.walk(tree):
            # 1. Resource Leaks: Unclosed file handles
            self._check_file_open(node)
            # 2. Resource Leaks: Sockets & HTTP sessions
            self._check_socket_and_http_sessions(node)
            # 3. Resource Leaks: Database cursors and connections
            self._check_database_connections(node)
            # 4. Bugs: Mutable default arguments
            self._check_mutable_default_args(node)
            # 5. Bugs: Bare except clauses
            self._check_bare_except(node)
            # 6. Bugs: Comparison with None using == or !=
            self._check_comparison_with_none(node)
            # 7. Memory: Unbounded global container modifications
            self._check_unbounded_global_mutation(node)
            # 8. Memory: Class with __del__ method
            self._check_class_with_del(node)
            # 9. Memory: Inefficient readlines()
            self._check_inefficient_readlines(node)

    def _get_line_snippet(self, start_line: int, end_line: Optional[int] = None) -> str:
        if not self.lines:
            return ""
        s = max(1, start_line)
        e = end_line if end_line and end_line >= s else s
        selected = self.lines[s - 1:e]
        return "".join(selected).strip()

    def _check_file_open(self, node: ast.AST):
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Call):
                func = node.value.func
                func_name = None
                if isinstance(func, ast.Name) and func.id == "open":
                    func_name = "open"
                
                if func_name:
                    target_name = "f"
                    if node.targets and isinstance(node.targets[0], ast.Name):
                        target_name = node.targets[0].id

                    line = node.lineno
                    original_line = self.lines[line - 1] if line <= len(self.lines) else ""
                    indent = len(original_line) - len(original_line.lstrip())
                    indent_str = original_line[:indent]

                    orig_snippet = original_line.strip()
                    open_call_str = orig_snippet.split("=", 1)[-1].strip()
                    proposed = f"{indent_str}with {open_call_str} as {target_name}:\n{indent_str}    # file operations with deterministic auto-close"

                    diff = "".join(difflib.unified_diff(
                        [original_line],
                        [f"{indent_str}with {open_call_str} as {target_name}:\n", f"{indent_str}    # (indent subsequent operations)\n"],
                        fromfile=f"a/{self.file_path}",
                        tofile=f"b/{self.file_path}",
                        lineterm="\n"
                    ))

                    self.findings.append(Finding(
                        id=f"f-{uuid.uuid4().hex[:8]}",
                        rule_id="PY-RES-001",
                        title="Resource Leak: Unclosed File Descriptor",
                        severity="warning",
                        category="resource_leak",
                        file_path=self.file_path,
                        line=node.lineno,
                        column=node.col_offset + 1,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        end_column=getattr(node, "end_col_offset", None),
                        description=f"File opened via `open()` assigned to `{target_name}` without a `with` context manager.",
                        code_snippet=orig_snippet,
                        suggested_fix=f"Wrap file operations with `with open(...) as {target_name}:`",
                        explanation="Opening files without a context manager delays closing until the garbage collector runs. Under high load, this exhausts OS file descriptors (EMFILE).",
                        is_potential_warning=True,
                        fixable=False,
                        original_code=original_line,
                        proposed_code=proposed,
                        unified_diff=diff,
                    ))

    def _check_socket_and_http_sessions(self, node: ast.AST):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            target_name = "conn"
            if node.targets and isinstance(node.targets[0], ast.Name):
                target_name = node.targets[0].id

            func = call.func
            full_name = ""
            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    full_name = f"{func.value.id}.{func.attr}"
            elif isinstance(func, ast.Name):
                full_name = func.id

            if full_name in ("socket.socket", "aiohttp.ClientSession", "requests.Session"):
                line = node.lineno
                orig_snippet = self._get_line_snippet(line)
                orig_line = self.lines[line - 1] if line <= len(self.lines) else ""
                indent = orig_line[:len(orig_line) - len(orig_line.lstrip())]

                async_prefix = "async " if "aiohttp" in full_name else ""
                proposed_line = f"{indent}{async_prefix}with {full_name}() as {target_name}:\n{indent}    # Operations..."

                diff = "".join(difflib.unified_diff(
                    [orig_line],
                    [f"{indent}{async_prefix}with {full_name}() as {target_name}:\n"],
                    fromfile=f"a/{self.file_path}",
                    tofile=f"b/{self.file_path}",
                    lineterm="\n"
                ))

                self.findings.append(Finding(
                    id=f"f-{uuid.uuid4().hex[:8]}",
                    rule_id="PY-RES-002",
                    title=f"Resource Leak: Unmanaged {full_name}",
                    severity="warning",
                    category="resource_leak",
                    file_path=self.file_path,
                    line=node.lineno,
                    column=node.col_offset + 1,
                    description=f"Instantiated `{full_name}` without a context manager block.",
                    code_snippet=orig_snippet,
                    suggested_fix=f"Use `{async_prefix}with {full_name}() as {target_name}:` to guarantee connection pool and socket cleanup.",
                    explanation="Unclosed sessions or sockets keep underlying TCP connections in ESTABLISHED / TIME_WAIT state, leading to socket leaks and connection pool starvation.",
                    is_potential_warning=True,
                    fixable=False,
                    original_code=orig_line,
                    proposed_code=proposed_line,
                    unified_diff=diff,
                ))

    def _check_database_connections(self, node: ast.AST):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            func = call.func
            attr_name = ""
            if isinstance(func, ast.Attribute):
                attr_name = func.attr
            elif isinstance(func, ast.Name):
                attr_name = func.id

            if attr_name in ("cursor", "get_connection", "connect"):
                target_name = "conn"
                if node.targets and isinstance(node.targets[0], ast.Name):
                    target_name = node.targets[0].id

                line = node.lineno
                orig_line = self.lines[line - 1] if line <= len(self.lines) else ""
                indent = orig_line[:len(orig_line) - len(orig_line.lstrip())]

                self.findings.append(Finding(
                    id=f"f-{uuid.uuid4().hex[:8]}",
                    rule_id="PY-RES-003",
                    title="Resource Leak: Database Connection or Cursor",
                    severity="warning",
                    category="resource_leak",
                    file_path=self.file_path,
                    line=node.lineno,
                    column=node.col_offset + 1,
                    description=f"Database resource `{target_name}` created outside a context manager.",
                    code_snippet=self._get_line_snippet(line),
                    suggested_fix=f"Wrap database operation with a context manager: `with ... as {target_name}:`",
                    explanation="If an exception is raised prior to close(), the connection remains reserved in the database pool.",
                    is_potential_warning=True,
                    fixable=False,
                    original_code=orig_line,
                    proposed_code=f"{indent}with ... as {target_name}:\n{indent}    # db query\n",
                    unified_diff="",
                ))

    def _check_mutable_default_args(self, node: ast.AST):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    type_name = "list" if isinstance(default, ast.List) else ("dict" if isinstance(default, ast.Dict) else "set")
                    line = default.lineno
                    orig_line = self.lines[line - 1] if line <= len(self.lines) else ""

                    diff_offset = len(node.args.args) - len(node.args.defaults)
                    arg_name = "arg"
                    for idx, d in enumerate(node.args.defaults):
                        if d is default and (idx + diff_offset) < len(node.args.args):
                            arg_name = node.args.args[idx + diff_offset].arg
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

                    self.findings.append(Finding(
                        id=f"f-{uuid.uuid4().hex[:8]}",
                        rule_id="PY-BUG-001",
                        title=f"Bug: Mutable Default Argument `{arg_name}`",
                        severity="error",
                        category="bug",
                        file_path=self.file_path,
                        line=line,
                        column=default.col_offset + 1,
                        description=f"Function `{node.name}` defines default `{arg_name}={type_name}()`. Mutable defaults persist and mutate across invocations.",
                        code_snippet=self._get_line_snippet(node.lineno),
                        suggested_fix=f"Use `{arg_name}=None` in signature and initialize `{arg_name} = {type_name}()` inside the function body.",
                        explanation="Default argument values are evaluated once when function definition is executed, NOT upon each function call. Any mutations are permanently shared across subsequent calls.",
                        is_potential_warning=False,
                        fixable=True,
                        original_code=orig_line,
                        proposed_code=f"{corrected_line}{init_statement}",
                        unified_diff=diff,
                    ))

    def _check_bare_except(self, node: ast.AST):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                line = node.lineno
                orig_line = self.lines[line - 1] if line <= len(self.lines) else ""
                indent = orig_line[:len(orig_line) - len(orig_line.lstrip())]
                fixed_line = f"{indent}except Exception:\n"

                diff = "".join(difflib.unified_diff(
                    [orig_line],
                    [fixed_line],
                    fromfile=f"a/{self.file_path}",
                    tofile=f"b/{self.file_path}",
                    lineterm="\n"
                ))

                self.findings.append(Finding(
                    id=f"f-{uuid.uuid4().hex[:8]}",
                    rule_id="PY-BUG-002",
                    title="Bug: Bare `except:` Catches BaseException",
                    severity="warning",
                    category="bug",
                    file_path=self.file_path,
                    line=line,
                    column=node.col_offset + 1,
                    description="Bare `except:` catches `KeyboardInterrupt`, `SystemExit`, and memory errors, preventing clean shutdowns.",
                    code_snippet=self._get_line_snippet(line),
                    suggested_fix="Replace `except:` with `except Exception:`",
                    explanation="`except:` catches all descendants of `BaseException`, masking Ctrl+C interrupt signals and process termination requests.",
                    is_potential_warning=False,
                    fixable=True,
                    original_code=orig_line,
                    proposed_code=fixed_line,
                    unified_diff=diff,
                ))

    def _check_comparison_with_none(self, node: ast.AST):
        if isinstance(node, ast.Compare):
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(comparator, ast.Constant) and comparator.value is None:
                    if isinstance(op, (ast.Eq, ast.NotEq)):
                        op_str = "==" if isinstance(op, ast.Eq) else "!="
                        better_op = "is" if isinstance(op, ast.Eq) else "is not"
                        line = node.lineno
                        orig_line = self.lines[line - 1] if line <= len(self.lines) else ""

                        fixed_line = orig_line.replace(f"== None", "is None").replace("!= None", "is not None")
                        diff = "".join(difflib.unified_diff(
                            [orig_line],
                            [fixed_line],
                            fromfile=f"a/{self.file_path}",
                            tofile=f"b/{self.file_path}",
                            lineterm="\n"
                        ))

                        self.findings.append(Finding(
                            id=f"f-{uuid.uuid4().hex[:8]}",
                            rule_id="PY-BUG-003",
                            title=f"Bug: Comparison with None Using `{op_str}`",
                            severity="information",
                            category="bug",
                            file_path=self.file_path,
                            line=line,
                            column=node.col_offset + 1,
                            description=f"Comparison with singleton `None` should use `{better_op}` identity instead of `{op_str}` equality.",
                            code_snippet=self._get_line_snippet(line),
                            suggested_fix=f"Replace `{op_str} None` with `{better_op} None`",
                            explanation="`== None` calls `__eq__` on the left operand which may be overridden to return falsy or truthy unexpectedly. `is None` is faster and evaluates identity directly.",
                            is_potential_warning=False,
                            fixable=True,
                            original_code=orig_line,
                            proposed_code=fixed_line,
                            unified_diff=diff,
                        ))

    def _check_unbounded_global_mutation(self, node: ast.AST):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                var_name = node.func.value.id
                method = node.func.attr
                if var_name in self._global_collections and method in ("append", "extend", "insert", "add"):
                    line = node.lineno
                    self.findings.append(Finding(
                        id=f"f-{uuid.uuid4().hex[:8]}",
                        rule_id="PY-MEM-001",
                        title=f"Potential Memory Leak: Unbounded Global `{var_name}.{method}()`",
                        severity="warning",
                        category="memory",
                        file_path=self.file_path,
                        line=line,
                        column=node.col_offset + 1,
                        description=f"Global module-level collection `{var_name}` is continuously appended inside functions without bounding or eviction.",
                        code_snippet=self._get_line_snippet(line),
                        suggested_fix=f"Use `collections.deque(maxlen=1000)` or add an explicit eviction/cleanup policy to prevent uncontrolled RSS memory growth.",
                        explanation="Global data structures modified during application execution retain references throughout the Python process lifetime, bypassing garbage collection.",
                        is_potential_warning=True,
                        fixable=False,
                        original_code=self.lines[line - 1] if line <= len(self.lines) else "",
                        proposed_code="",
                        unified_diff="",
                    ))

    def _check_class_with_del(self, node: ast.AST):
        if isinstance(node, ast.ClassDef):
            has_del = any(isinstance(b, ast.FunctionDef) and b.name == "__del__" for b in node.body)
            if has_del:
                line = node.lineno
                self.findings.append(Finding(
                    id=f"f-{uuid.uuid4().hex[:8]}",
                    rule_id="PY-MEM-002",
                    title=f"Memory Leak Risk: Custom `__del__` Destructor in `{node.name}`",
                    severity="warning",
                    category="memory",
                    file_path=self.file_path,
                    line=line,
                    column=node.col_offset + 1,
                    description=f"Class `{node.name}` implements `__del__`. Cyclic references involving `__del__` can prevent cyclic garbage collector from reclaiming memory.",
                    code_snippet=self._get_line_snippet(line),
                    suggested_fix="Prefer explicit context managers (`__enter__` and `__exit__`) or `weakref` references over `__del__` finalizers.",
                    explanation="In CPython, circular references containing objects with custom `__del__` methods cannot be safely garbage collected without knowing destructor ordering.",
                    is_potential_warning=True,
                    fixable=False,
                    original_code=self.lines[line - 1] if line <= len(self.lines) else "",
                    proposed_code="",
                    unified_diff="",
                ))

    def _check_inefficient_readlines(self, node: ast.AST):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "readlines":
                line = node.lineno
                orig_line = self.lines[line - 1] if line <= len(self.lines) else ""
                
                fixed_line = orig_line.replace(".readlines()", "")
                diff = "".join(difflib.unified_diff(
                    [orig_line],
                    [fixed_line],
                    fromfile=f"a/{self.file_path}",
                    tofile=f"b/{self.file_path}",
                    lineterm="\n"
                ))

                self.findings.append(Finding(
                    id=f"f-{uuid.uuid4().hex[:8]}",
                    rule_id="PY-MEM-003",
                    title="Memory Optimization: Full-File `readlines()`",
                    severity="information",
                    category="memory",
                    file_path=self.file_path,
                    line=line,
                    column=node.col_offset + 1,
                    description="Calling `.readlines()` loads entire file contents into a Python list in memory at once.",
                    code_snippet=self._get_line_snippet(line),
                    suggested_fix="Iterate directly over file handle: `for line in file_obj:` to stream lines in O(1) memory.",
                    explanation="Direct iteration streams lines incrementally without allocating the whole file as a list in memory.",
                    is_potential_warning=False,
                    fixable=True,
                    original_code=orig_line,
                    proposed_code=fixed_line,
                    unified_diff=diff,
                ))
