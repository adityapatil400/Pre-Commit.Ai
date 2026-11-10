# PreCommit AI — Static Python AST Analysis Platform

> **Tagline:** Catch Bugs & Leakages Before They Commit.

PreCommit AI is a Python AST-based static code analysis platform that helps developers identify syntax errors, potential memory leaks, resource leaks, unclosed files/connections, and suspicious resource-management patterns before committing code.

**Security Guarantee:** Zero source code execution. Code is statically analyzed using Python's Abstract Syntax Tree (`ast`).

---

## 9-Step Pipeline Overview

1. **Input Handling**: Accepts single `.py` Python files, `.zip` project archives, or GitHub repository URLs (`https://github.com/owner/repo`).
2. **Source Code Retrieval**: Safely extracts files in memory with path traversal (Zip-Slip) protection or fetches via GitHub REST API / zipball.
3. **AST-Based Analysis**: Compiles and parses source code purely via Python `ast.parse()` without running, executing, or importing code.
4. **Issue Detection**:
   - **Syntax Errors**: Parser compilation failures, unclosed delimiters, indentation errors (`PY-SYN-001`).
   - **Resource Leaks**: Unclosed files (`PY-RES-001`), sockets/HTTP client sessions (`PY-RES-002`), database connections & cursors (`PY-RES-003`), unmanaged subprocesses (`PY-RES-004`).
   - **Memory Leaks**: Unbounded global collection mutations (`PY-MEM-001`), circular references with custom `__del__` destructors (`PY-MEM-002`), and high-memory full-file reads (`PY-MEM-003`).
   - **Bugs & Antipatterns**: Mutable default arguments (`PY-BUG-001`), bare `except:` catching BaseException (`PY-BUG-002`), identity comparisons using `== None` (`PY-BUG-003`).
5. **Fix Recommendation Engine**: Automatically generates suggested remediations, technical explanations, and unified / side-by-side diffs.
6. **User Approval**: Interactive UI displays original code vs suggested code. Users can accept or reject each fix individually or batch-approve.
7. **Code Validation**: Re-parses the proposed code in memory using `ast.parse` and re-runs all static checks to ensure zero syntax errors before applying.
8. **GitHub Commit**: For GitHub repository inputs, creates a dedicated branch (`precommit-ai/fixes-<timestamp>`) and commits only approved fixes. For file/ZIP inputs, provides a downloadable patched archive.
9. **Final Report**: Displays updated files, commit information/URL, remaining issues, and exports clean Markdown / JSON reports.

---

## Running the Application

### 1. Start Backend Server (FastAPI)
```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Start Frontend Dev Server (Vite + React)
```bash
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 3. Run Automated Tests
```bash
PYTHONPATH=. python3 tests/test_backend_pipeline.py
npm run build
```

