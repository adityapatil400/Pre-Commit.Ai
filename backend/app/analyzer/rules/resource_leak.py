import ast
import difflib
import uuid
from typing import Dict, List, Optional, Set

from backend.app.schemas.analysis_schema import FindingSchema, SeverityEnum

class ResourceLeakVisitor(ast.NodeVisitor):
    """
    AST NodeVisitor that inspects resource management patterns:
    - RESOURCE001: Files opened without clearly identifiable close or context manager
    - RESOURCE002: Connections / sockets potentially left open
    - RESOURCE003: Resource cleanup missing from exception-handling (try-finally) paths
    - RESOURCE004: Suspicious subprocess.Popen resource handling
    """

    def __init__(self, file_path: str, lines: List[str]):
        super().__init__()
        self.file_path = file_path
        self.lines = lines
        self.findings: List[FindingSchema] = []
        
        # Track variables managed by with statements
        self.with_context_vars: Set[str] = set()
        # Track variables explicitly closed via .close()
        self.explicitly_closed_vars: Set[str] = set()

    def _get_line_text(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1]
        return ""

    def visit_With(self, node: ast.With):
        for item in node.items:
            if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                self.with_context_vars.add(item.optional_vars.id)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        for item in node.items:
            if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                self.with_context_vars.add(item.optional_vars.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Track .close() calls
        if isinstance(node.func, ast.Attribute) and node.func.attr == "close":
            if isinstance(node.func.value, ast.Name):
                self.explicitly_closed_vars.add(node.func.value.id)

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        if not isinstance(node.value, ast.Call):
            self.generic_visit(node)
            return

        call = node.value
        target_name = ""
        if node.targets and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id

        func_name = ""
        if isinstance(call.func, ast.Name):
            func_name = call.func.id
        elif isinstance(call.func, ast.Attribute):
            if isinstance(call.func.value, ast.Name):
                func_name = f"{call.func.value.id}.{call.func.attr}"
            else:
                func_name = call.func.attr

        line_num = node.lineno
        line_text = self._get_line_text(line_num)
        snippet = line_text.strip()
        indent = line_text[:len(line_text) - len(line_text.lstrip())]

        # 1. RESOURCE001: Unclosed file descriptor
        if func_name == "open" or func_name.endswith(".open"):
            # Check if assigned variable is in with-context
            if target_name and target_name not in self.with_context_vars:
                open_str = snippet.split("=", 1)[-1].strip()
                proposed = f"{indent}with {open_str} as {target_name}:\n{indent}    # Operations inside context manager\n"
                diff = "".join(difflib.unified_diff(
                    [line_text],
                    [proposed],
                    fromfile=f"a/{self.file_path}",
                    tofile=f"b/{self.file_path}",
                    lineterm="\n"
                ))

                self.findings.append(FindingSchema(
                    id=f"res-{uuid.uuid4().hex[:8]}",
                    rule_id="RESOURCE001",
                    category="resource_leak",
                    severity=SeverityEnum.WARNING,
                    title="Potential unclosed file",
                    file_path=self.file_path,
                    line_number=line_num,
                    line=line_num,
                    column=node.col_offset + 1,
                    description="The opened file may not be closed on every execution path.",
                    suggestion="Consider using a context manager ('with open(...) as f:').",
                    suggested_fix="Consider using a context manager ('with open(...) as f:').",
                    code_snippet=snippet,
                    explanation="Leaving files open relies on garbage collection and can exhaust OS file descriptors (EMFILE).",
                    is_potential_warning=True,
                    fixable=False,
                    original_code=line_text,
                    proposed_code=proposed,
                    unified_diff=diff
                ))

        # 2. RESOURCE002: Network / Database Connection potentially left open
        conn_funcs = (
            "socket.socket",
            "http.client.HTTPConnection",
            "http.client.HTTPSConnection",
            "urllib.request.urlopen",
            "aiohttp.ClientSession",
            "requests.Session",
            "sqlite3.connect",
            "psycopg2.connect",
            "pymysql.connect",
        )
        if any(func_name == cf or func_name.endswith(f".{cf}") for cf in conn_funcs):
            if target_name and target_name not in self.with_context_vars:
                self.findings.append(FindingSchema(
                    id=f"res-{uuid.uuid4().hex[:8]}",
                    rule_id="RESOURCE002",
                    category="resource_leak",
                    severity=SeverityEnum.WARNING,
                    title="Potential unclosed network or database connection",
                    file_path=self.file_path,
                    line_number=line_num,
                    line=line_num,
                    column=node.col_offset + 1,
                    description=f"Resource '{func_name}' is acquired without an enclosing context manager or explicit close handler.",
                    suggestion="Acquire connections using a context manager ('with') or close them in a finally block.",
                    suggested_fix="Acquire connections using a context manager ('with') or close them in a finally block.",
                    code_snippet=snippet,
                    explanation="Unclosed connections cause socket leaks and pool exhaustion.",
                    is_potential_warning=True,
                    fixable=False,
                    original_code=line_text,
                    proposed_code="",
                    unified_diff=""
                ))

        # 3. RESOURCE004: Suspicious subprocess resource handling
        if func_name in ("subprocess.Popen", "Popen"):
            if target_name and target_name not in self.with_context_vars:
                self.findings.append(FindingSchema(
                    id=f"res-{uuid.uuid4().hex[:8]}",
                    rule_id="RESOURCE004",
                    category="resource_leak",
                    severity=SeverityEnum.WARNING,
                    title="Unmanaged subprocess Popen lifecycle",
                    file_path=self.file_path,
                    line_number=line_num,
                    line=line_num,
                    column=node.col_offset + 1,
                    description=f"Subprocess '{target_name}' (subprocess.Popen) instantiated without context manager or lifecycle tracking.",
                    suggestion="Use a context manager with subprocess.Popen or ensure process is terminated/waited on.",
                    suggested_fix="Use a context manager with subprocess.Popen or ensure process is terminated/waited on.",
                    code_snippet=snippet,
                    explanation="Unmanaged subprocesses can become zombie processes or leave pipes unclosed.",
                    is_potential_warning=True,
                    fixable=False,
                    original_code=line_text,
                    proposed_code="",
                    unified_diff=""
                ))

        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        # 4. RESOURCE003: Resource cleanup missing from exception handling paths
        # Inspect statements in try block: if open or socket call is present, check for finally block
        acquired_resources = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                fname = ""
                if isinstance(call.func, ast.Name):
                    fname = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    fname = call.func.attr
                if fname in ("open", "socket", "connect", "urlopen") and stmt.targets:
                    if isinstance(stmt.targets[0], ast.Name):
                        acquired_resources.append((stmt.targets[0].id, stmt.lineno))

        if acquired_resources and not node.finalbody:
            for rname, rline in acquired_resources:
                snippet = self._get_line_text(rline).strip()
                self.findings.append(FindingSchema(
                    id=f"res-{uuid.uuid4().hex[:8]}",
                    rule_id="RESOURCE003",
                    category="resource_leak",
                    severity=SeverityEnum.WARNING,
                    title="Resource cleanup missing from exception-handling path",
                    file_path=self.file_path,
                    line_number=rline,
                    line=rline,
                    column=1,
                    description=f"Resource '{rname}' acquired in try-block without a corresponding 'finally:' cleanup block.",
                    suggestion="Ensure resource cleanup (e.g. .close()) is performed in a 'finally:' block.",
                    suggested_fix="Ensure resource cleanup (e.g. .close()) is performed in a 'finally:' block.",
                    code_snippet=snippet,
                    explanation="If an exception occurs between acquisition and close, the resource remains unclosed.",
                    is_potential_warning=True,
                    fixable=False,
                    original_code=self._get_line_text(rline),
                    proposed_code="",
                    unified_diff=""
                ))

        self.generic_visit(node)

class ResourceLeakChecker:
    """
    Backwards compatibility wrapper delegating to ResourceLeakVisitor.
    """
    @classmethod
    def check_node(cls, node: ast.AST, file_path: str, lines: List[str]) -> List[FindingSchema]:
        visitor = ResourceLeakVisitor(file_path=file_path, lines=lines)
        visitor.visit(node)
        return visitor.findings
