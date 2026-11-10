import ast
import uuid
from typing import List, Set

from backend.app.schemas.analysis_schema import FindingSchema, SeverityEnum

class MemoryLeakVisitor(ast.NodeVisitor):
    """
    AST NodeVisitor that statically identifies suspicious memory-retention patterns:
    - MEMORY001: Unbounded collection growth in global/module collections
    - MEMORY002: Circular reference hazards with custom __del__ destructors
    - MEMORY003: High memory retention via unbuffered readlines()
    - MEMORY004: Suspicious global reference mutation inside functions
    - MEMORY005: Object retention in nested closures / callbacks
    """

    def __init__(self, file_path: str, lines: List[str], global_collections: Set[str] = None):
        super().__init__()
        self.file_path = file_path
        self.lines = lines
        self.findings: List[FindingSchema] = []
        self.global_collections: Set[str] = global_collections if global_collections is not None else set()
        self.in_function = False
        self.current_function: List[str] = []

    def _get_line_text(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1]
        return ""

    def visit_Module(self, node: ast.Module):
        # Discover top-level collections
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(stmt.value, (ast.List, ast.Dict, ast.Set)):
                            self.global_collections.add(target.id)
                        elif isinstance(stmt.value, ast.Call):
                            fname = ""
                            if isinstance(stmt.value.func, ast.Name):
                                fname = stmt.value.func.id
                            if fname in ("list", "dict", "set"):
                                self.global_collections.add(target.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.current_function.append(node.name)
        old_in_func = self.in_function
        self.in_function = True

        # Check for nested closure capturing outer state (MEMORY005)
        if len(self.current_function) > 1:
            line = node.lineno
            line_text = self._get_line_text(line)
            snippet = line_text.strip()
            self.findings.append(FindingSchema(
                id=f"mem-{uuid.uuid4().hex[:8]}",
                rule_id="MEMORY005",
                category="memory_leak",
                severity=SeverityEnum.WARNING,
                title="Potential object retention in nested closure or callback",
                file_path=self.file_path,
                line_number=line,
                line=line,
                column=node.col_offset + 1,
                description=f"Nested function or closure '{node.name}' may retain references to outer scope variables.",
                suggestion="Verify that long-lived closures or event callbacks do not unintentionally retain large outer scope objects.",
                suggested_fix="Verify that long-lived closures or event callbacks do not unintentionally retain large outer scope objects.",
                code_snippet=snippet,
                explanation="Closures retain their enclosing lexical environment, which can prevent garbage collection of outer data structures.",
                is_potential_warning=True,
                fixable=False,
                original_code=line_text,
                proposed_code="",
                unified_diff=""
            ))

        self.generic_visit(node)
        self.in_function = old_in_func
        self.current_function.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)  # re-use logic

    def visit_Call(self, node: ast.Call):
        line = node.lineno
        line_text = self._get_line_text(line)
        snippet = line_text.strip()

        # 1. MEMORY001: Unbounded collection growth
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                var_name = node.func.value.id
                method = node.func.attr
                if var_name in self.global_collections and method in ("append", "extend", "insert", "add"):
                    self.findings.append(FindingSchema(
                        id=f"mem-{uuid.uuid4().hex[:8]}",
                        rule_id="MEMORY001",
                        category="memory_leak",
                        severity=SeverityEnum.WARNING,
                        title=f"Potential unbounded collection growth ({var_name}.{method})",
                        file_path=self.file_path,
                        line_number=line,
                        line=line,
                        column=node.col_offset + 1,
                        description=f"Global module-level collection '{var_name}' is appended to inside function '{self.current_function[-1] if self.current_function else '<module>'}' without visible bound or eviction.",
                        suggestion="Consider using collections.deque with maxlen or an explicit eviction cache (e.g. functools.lru_cache).",
                        suggested_fix="Consider using collections.deque with maxlen or an explicit eviction cache (e.g. functools.lru_cache).",
                        code_snippet=snippet,
                        explanation="Module-level data structures modified continuously during execution retain references indefinitely.",
                        is_potential_warning=True,
                        fixable=False,
                        original_code=line_text,
                        proposed_code="",
                        unified_diff=""
                    ))

            # 2. MEMORY003: Unbuffered .readlines() loading entire file
            if node.func.attr == "readlines" or (node.func.attr == "read" and not node.args):
                self.findings.append(FindingSchema(
                    id=f"mem-{uuid.uuid4().hex[:8]}",
                    rule_id="MEMORY003",
                    category="memory_leak",
                    severity=SeverityEnum.WARNING,
                    title="Potential high memory retention via unbuffered read",
                    file_path=self.file_path,
                    line_number=line,
                    line=line,
                    column=node.col_offset + 1,
                    description=f"Call to '{node.func.attr}()' reads entire content into memory at once.",
                    suggestion="Iterate line-by-line ('for line in f:') or read in bounded chunks to reduce peak memory usage.",
                    suggested_fix="Iterate line-by-line ('for line in f:') or read in bounded chunks to reduce peak memory usage.",
                    code_snippet=snippet,
                    explanation="Reading large files entirely into memory can cause sudden heap spikes and OOM termination.",
                    is_potential_warning=True,
                    fixable=False,
                    original_code=line_text,
                    proposed_code="",
                    unified_diff=""
                ))

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        # 3. MEMORY002: Class implementing __del__ destructor
        has_del = any(isinstance(b, ast.FunctionDef) and b.name == "__del__" for b in node.body)
        if has_del:
            line = node.lineno
            line_text = self._get_line_text(line)
            snippet = line_text.strip()
            self.findings.append(FindingSchema(
                id=f"mem-{uuid.uuid4().hex[:8]}",
                rule_id="MEMORY002",
                category="memory_leak",
                severity=SeverityEnum.WARNING,
                title=f"Potential cyclic reference hazard with '__del__' in class '{node.name}'",
                file_path=self.file_path,
                line_number=line,
                line=line,
                column=node.col_offset + 1,
                description=f"Class '{node.name}' implements a custom '__del__' destructor. Circular references involving '__del__' complicate garbage collection.",
                suggestion="Prefer explicit context managers or weakref (weakref.ref / weakref.proxy) over custom '__del__' methods.",
                suggested_fix="Prefer explicit context managers or weakref (weakref.ref / weakref.proxy) over custom '__del__' methods.",
                code_snippet=snippet,
                explanation="Circular references containing objects with custom __del__ methods are difficult for the garbage collector to reclaim.",
                is_potential_warning=True,
                fixable=False,
                original_code=line_text,
                proposed_code="",
                unified_diff=""
            ))

        self.generic_visit(node)

    def visit_Global(self, node: ast.Global):
        # 4. MEMORY004: Suspicious global reference mutation
        line = node.lineno
        line_text = self._get_line_text(line)
        snippet = line_text.strip()
        var_names = ", ".join(node.names)

        self.findings.append(FindingSchema(
            id=f"mem-{uuid.uuid4().hex[:8]}",
            rule_id="MEMORY004",
            category="memory_leak",
            severity=SeverityEnum.WARNING,
            title=f"Potential memory retention via global reference '{var_names}'",
            file_path=self.file_path,
            line_number=line,
            line=line,
            column=node.col_offset + 1,
            description=f"Function modifies global variable(s) '{var_names}'. Global references persist for the lifetime of the process.",
            suggestion="Avoid mutating global state inside functions; pass state explicitly or use scoped objects.",
            suggested_fix="Avoid mutating global state inside functions; pass state explicitly or use scoped objects.",
            code_snippet=snippet,
            explanation="Global variables persist across the runtime lifetime and prevent objects from being collected.",
            is_potential_warning=True,
            fixable=False,
            original_code=line_text,
            proposed_code="",
            unified_diff=""
        ))
        self.generic_visit(node)

class MemoryLeakChecker:
    """
    Backwards compatibility wrapper delegating to MemoryLeakVisitor.
    """
    @classmethod
    def check_node(
        cls,
        node: ast.AST,
        file_path: str,
        lines: List[str],
        global_collections: Set[str]
    ) -> List[FindingSchema]:
        visitor = MemoryLeakVisitor(file_path=file_path, lines=lines, global_collections=global_collections)
        visitor.visit(node)
        return visitor.findings
