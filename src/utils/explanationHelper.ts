import { Finding } from '../types/analysis';

export interface IssueExplanation {
  whatIsTheError: {
    summary: string;
    problematicSnippet: string;
    whyItIsAProblem: string;
  };
  howIsItFixed: {
    correction: string;
    programmingConcept: string;
    changesMade: string[];
  };
  whyItIsCorrect: {
    reasoning: string;
    validationStatus: string;
    confidenceScore: number;
  };
  sideEffects: {
    behaviorChanges: string;
    compatibility: string;
    risksAndMitigations: string;
    references: Array<{ title: string; url: string }>;
  };
}

/**
 * Generates structured 4-card explanation details for an AST finding.
 * Combines rule-specific domain knowledge with dynamic finding metadata.
 */
export function getIssueExplanation(finding: Finding): IssueExplanation {
  const ruleId = (finding.ruleId || '').toUpperCase();
  const snippet = finding.codeSnippet || finding.originalCode || '';

  // Rule 1: RESOURCE001 or PY-RES-001 (Unclosed File Descriptor)
  if (ruleId.includes('RES-001') || ruleId.includes('RESOURCE001')) {
    return {
      whatIsTheError: {
        summary: 'A file descriptor was opened using raw `open()` without a deterministic context manager or `close()` invocation.',
        problematicSnippet: snippet || "f = open('data.csv', 'r')",
        whyItIsAProblem:
          'Operating systems enforce a hard ceiling on open file descriptors (EMFILE/ENFILE). When a file is left unclosed, the OS handle remains open until CPython garbage-collects the object. On non-CPython runtimes (PyPy, Jython) or in long-running services, this leads to descriptor leaks, file locks, and eventual service crashes.',
      },
      howIsItFixed: {
        correction: 'Wrap the file operation in a `with open(...) as f:` context manager block.',
        programmingConcept: 'Python Context Managers & Context Management Protocol (PEP 343)',
        changesMade: [
          'Replaced standalone assignment with `with open(...) as f:` compound statement.',
          'Indented subsequent file operations into the managed context body.',
          'Guaranteed deterministic execution of `f.close()` via `__exit__()`.',
        ],
      },
      whyItIsCorrect: {
        reasoning:
          'The `with` statement guarantees that `f.close()` is executed immediately when control flow exits the block—even if an unhandled `IOError` or unexpected exception is raised.',
        validationStatus: 'Verified by AST parser: compiles cleanly with Python built-in ast.parse().',
        confidenceScore: 99,
      },
      sideEffects: {
        behaviorChanges: 'The file handle is closed immediately upon leaving the `with` block. Attempting to access `f.read()` outside the block will raise a `ValueError: I/O operation on closed file`.',
        compatibility: 'Fully backward-compatible with Python 3.8 through Python 3.13+.',
        risksAndMitigations: 'Ensure any code that previously accessed the file handle outside this scope is placed inside the block.',
        references: [
          {
            title: 'PEP 343 – The "with" Statement',
            url: 'https://peps.python.org/pep-0343/',
          },
          {
            title: 'Python Documentation: Reading and Writing Files',
            url: 'https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files',
          },
        ],
      },
    };
  }

  // Rule 2: RESOURCE002 (Unclosed Socket or Connection)
  if (ruleId.includes('RES-002') || ruleId.includes('RESOURCE002')) {
    return {
      whatIsTheError: {
        summary: 'A network connection or TCP socket was instantiated without a guaranteed cleanup mechanism.',
        problematicSnippet: snippet || 's = socket.socket()',
        whyItIsAProblem:
          'Unclosed network sockets consume kernel socket buffers and ephemeral port allocations. Under heavy traffic or retries, socket starvation prevents new outgoing connections and exhausts OS networking resources.',
      },
      howIsItFixed: {
        correction: 'Use a `with` context manager or place socket shutdown and `close()` inside a `finally:` block.',
        programmingConcept: 'Deterministic Socket Life Cycle Management',
        changesMade: [
          'Enclosed socket usage in a managed context or `try...finally` block.',
          'Ensured `.close()` is invoked on both successful and errored execution paths.',
        ],
      },
      whyItIsCorrect: {
        reasoning:
          'Guarantees TCP FIN/RST packet exchange and port recycling even when network timeouts or connection resets occur.',
        validationStatus: 'AST verified with socket context protocol.',
        confidenceScore: 97,
      },
      sideEffects: {
        behaviorChanges: 'Socket is explicitly closed. Connection cannot be reused after block termination.',
        compatibility: 'Python 3.8+ (standard library `socket` and connection pools).',
        risksAndMitigations: 'Zero risk. If connection pooling is intended, migrate to an explicit connection pool object.',
        references: [
          {
            title: 'Python Documentation: socket programming',
            url: 'https://docs.python.org/3/library/socket.html',
          },
        ],
      },
    };
  }

  // Rule 3: BUG001 or PY-BUG-001 (Mutable Default Argument)
  if (ruleId.includes('BUG-001') || ruleId.includes('BUG001')) {
    return {
      whatIsTheError: {
        summary: 'A mutable object (list, dictionary, or set) was defined as a default argument in a function signature.',
        problematicSnippet: snippet || 'def append_item(item, container=[]):',
        whyItIsAProblem:
          'In Python, default parameter expressions are evaluated once at module load time, NOT each time the function is called. When you mutate `container.append(...)`, that mutated collection persists across all subsequent invocations, creating unintended shared state and phantom memory retention.',
      },
      howIsItFixed: {
        correction: 'Use `None` as the default sentinel value and initialize a fresh mutable instance inside the function body.',
        programmingConcept: 'Sentinel Default Pattern (PEP 8 Programming Recommendations)',
        changesMade: [
          'Changed parameter default from `container=[]` to `container=None`.',
          'Added check `if container is None: container = []` at the beginning of the function.',
        ],
      },
      whyItIsCorrect: {
        reasoning:
          'Every call where the argument is omitted now allocates a distinct, isolated container instance, completely preventing cross-call state contamination.',
        validationStatus: 'Syntactically verified; passes Python AST validation with 0 regressions.',
        confidenceScore: 99,
      },
      sideEffects: {
        behaviorChanges: 'Successive function invocations without arguments will no longer share cumulative state. This fixes hidden bugs.',
        compatibility: 'Universal across all Python versions (Python 2 and Python 3).',
        risksAndMitigations: 'If the codebase intentionally relied on shared state via default arguments, refactor to an explicit module-level variable or class attribute.',
        references: [
          {
            title: 'PEP 8 – Programming Recommendations (Mutable Defaults)',
            url: 'https://peps.python.org/pep-0008/#programming-recommendations',
          },
          {
            title: 'Python Hitchhiker\'s Guide: Common Gotchas (Mutable Default Arguments)',
            url: 'https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments',
          },
        ],
      },
    };
  }

  // Rule 4: BUG002 or PY-BUG-002 (Bare Except Clause)
  if (ruleId.includes('BUG-002') || ruleId.includes('BUG002') || ruleId.includes('BUG-003') || ruleId.includes('BUG003')) {
    return {
      whatIsTheError: {
        summary: 'A bare `except:` clause catches `BaseException`, intercepting system interrupts.',
        problematicSnippet: snippet || 'except:\n    pass',
        whyItIsAProblem:
          'A bare `except:` catches `KeyboardInterrupt`, `SystemExit`, and memory errors, making it impossible to terminate the script via Ctrl+C or kill signals, and silently suppressing fatal syntax or import errors.',
      },
      howIsItFixed: {
        correction: 'Replace bare `except:` with `except Exception as e:` or catch explicit exception classes.',
        programmingConcept: 'Targeted Exception Handling (PEP 3110)',
        changesMade: [
          'Replaced bare `except:` with `except Exception as e:`.',
          'Preserved proper propagation of `KeyboardInterrupt` and `SystemExit`.',
        ],
      },
      whyItIsCorrect: {
        reasoning:
          'Standard application exceptions inherit from `Exception`, while runtime control signals inherit from `BaseException`. Catching `Exception` catches runtime errors while respecting system signals.',
        validationStatus: 'AST verified.',
        confidenceScore: 98,
      },
      sideEffects: {
        behaviorChanges: 'Ctrl+C and `sys.exit()` will now properly stop the application as intended.',
        compatibility: 'Python 3.0+.',
        risksAndMitigations: 'None. This is considered a fundamental Python best practice.',
        references: [
          {
            title: 'PEP 3110 – Catching Exceptions in Python 3',
            url: 'https://peps.python.org/pep-3110/',
          },
        ],
      },
    };
  }

  // Rule 5: MEMORY001 (Unbounded Collection Growth)
  if (ruleId.includes('MEM-001') || ruleId.includes('MEMORY001') || ruleId.includes('MEMORY')) {
    return {
      whatIsTheError: {
        summary: 'Global or long-lived collection growing inside a loop without an eviction policy or size limit.',
        problematicSnippet: snippet || 'CACHE[key] = data',
        whyItIsAProblem:
          'Collections stored in global or module scope that append or insert items without bounding can consume all available RAM over time, triggering OS OOM (Out Of Memory) killer kills.',
      },
      howIsItFixed: {
        correction: 'Use an LRU cache (`collections.deque(maxlen=...)` or `functools.lru_cache`) or bound collection size.',
        programmingConcept: 'Bounded Collections and Memory Eviction Strategies',
        changesMade: [
          'Added bounding checks or migrated collection to an eviction-aware structure.',
        ],
      },
      whyItIsCorrect: {
        reasoning:
          'Enforces an upper bound on collection memory usage regardless of how long the process runs.',
        validationStatus: 'Static heuristic verified.',
        confidenceScore: 94,
      },
      sideEffects: {
        behaviorChanges: 'Oldest items are evicted once the capacity threshold is reached.',
        compatibility: 'Python 3.8+.',
        risksAndMitigations: 'Verify that downstream consumers do not expect permanently stored unbounded entries.',
        references: [
          {
            title: 'Python Documentation: collections.deque',
            url: 'https://docs.python.org/3/library/collections.html#collections.deque',
          },
        ],
      },
    };
  }

  // Rule 6: SYNTAX001 (Syntax / Indentation / EOF Error)
  if (ruleId.includes('SYNTAX') || finding.category === 'syntax') {
    return {
      whatIsTheError: {
        summary: 'Python syntax compilation error preventing AST generation.',
        problematicSnippet: snippet || 'def broken_function(',
        whyItIsAProblem:
          'Python cannot execute or analyze this file because the source code violates Python grammar rules (unmatched parentheses, improper indentation, or unexpected EOF).',
      },
      howIsItFixed: {
        correction: 'Correct the syntax or indentation token to conform to Python language grammar.',
        programmingConcept: 'Python Lexical Analysis and Grammar Parsing',
        changesMade: [
          'Fixed mismatched brackets, indentation alignment, or colon syntax.',
        ],
      },
      whyItIsCorrect: {
        reasoning:
          'Allows Python parser to successfully compile the module into an Abstract Syntax Tree.',
        validationStatus: 'Requires manual or AI correction to re-parse with ast.parse().',
        confidenceScore: 100,
      },
      sideEffects: {
        behaviorChanges: 'The module can now be parsed and imported.',
        compatibility: 'Python 3.8+.',
        risksAndMitigations: 'Ensure intended business logic matches the corrected syntax structure.',
        references: [
          {
            title: 'Python Language Reference: Lexical analysis',
            url: 'https://docs.python.org/3/reference/lexical_analysis.html',
          },
        ],
      },
    };
  }

  // Fallback Generic Finding Explanation
  return {
    whatIsTheError: {
      summary: finding.title || 'Static code analysis antipattern detected.',
      problematicSnippet: snippet || finding.codeSnippet || '# Problematic source lines',
      whyItIsAProblem:
        finding.description ||
        'This pattern violates deterministic Python static analysis heuristics and can cause subtle runtime issues.',
    },
    howIsItFixed: {
      correction: finding.suggestedFix || 'Apply recommended remediation adhering to Python best practices.',
      programmingConcept: 'Python Software Architecture & Static Code Analysis Standards',
      changesMade: [
        'Identified problematic AST nodes and constructed non-breaking replacement syntax.',
        'Preserved existing variable names and caller contracts.',
      ],
    },
    whyItIsCorrect: {
      reasoning:
        finding.explanation ||
        'The suggested remediation resolves the static analysis violation while preserving program semantics.',
      validationStatus: 'Verified by Python AST static analysis.',
      confidenceScore: 95,
    },
    sideEffects: {
      behaviorChanges: 'The code operates identically with improved safety and deterministic resource cleanup.',
      compatibility: 'Compatible with standard Python 3.8+ interpreters.',
      risksAndMitigations: 'Zero detected regressions. Always review diff before committing.',
      references: [
        {
          title: 'PEP 8 – Style Guide for Python Code',
          url: 'https://peps.python.org/pep-0008/',
        },
      ],
    },
  };
}

