import ast
import io
from pathlib import Path
from typing import Iterator, Optional, Tuple, Union
import tokenize

from backend.app.utils.logger import logger

class ASTParsingException(Exception):
    """Raised when source reading or AST generation encounters an unrecoverable failure."""
    pass

class ParseResult:
    """
    Encapsulates the result of parsing Python source code with ast.parse().
    Supports tuple unpacking: `tree, err = parse_result` for backwards compatibility.
    """
    def __init__(
        self,
        success: bool,
        tree: Optional[ast.AST],
        syntax_error: Optional[SyntaxError],
        filename: str,
        source_code: str = "",
        encoding: str = "utf-8"
    ):
        self.success = success
        self.tree = tree
        self.syntax_error = syntax_error
        self.filename = filename
        self.source_code = source_code
        self.encoding = encoding

    def __iter__(self) -> Iterator:
        yield self.tree
        yield self.syntax_error

    def __repr__(self) -> str:
        return (
            f"ParseResult(success={self.success}, filename='{self.filename}', "
            f"has_tree={self.tree is not None}, error={self.syntax_error})"
        )

class ASTParser:
    """
    Safely parses Python source files into Abstract Syntax Trees (AST).
    
    Guarantees:
    - Zero runtime code execution (strictly static AST parsing).
    - Robust encoding resolution with fallback.
    - Accurate tracking of filename and syntax error locations.
    """

    @staticmethod
    def read_source_file(file_path: Union[str, Path]) -> Tuple[str, str]:
        """
        Reads a Python file from disk as text.
        Handles PEP 263 encoding cookies, defaults to UTF-8, and falls back gracefully.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")

        raw_bytes = path.read_bytes()

        # Reject binary files containing null bytes
        if b"\x00" in raw_bytes[:1024]:
            raise UnicodeDecodeError(
                "utf-8", raw_bytes, 0, 1,
                "Binary null byte detected in source code"
            )

        # 1. Try Python's official PEP 263 encoding detection
        try:
            encoding, _ = tokenize.detect_encoding(io.BytesIO(raw_bytes).readline)
            source_text = raw_bytes.decode(encoding)
            return source_text, encoding
        except (SyntaxError, UnicodeDecodeError):
            pass

        # 2. Try UTF-8 fallback
        try:
            source_text = raw_bytes.decode("utf-8")
            return source_text, "utf-8"
        except UnicodeDecodeError:
            pass

        # 3. Try Latin-1 fallback
        try:
            source_text = raw_bytes.decode("latin-1")
            return source_text, "latin-1"
        except UnicodeDecodeError as e:
            raise e

    @classmethod
    def parse_source(
        cls,
        source_code: str,
        filename: str = "<unknown>"
    ) -> ParseResult:
        """
        Parses source code string into an AST structure using ast.parse().
        Never executes any code.
        """
        try:
            tree = ast.parse(source_code, filename=filename)
            return ParseResult(
                success=True,
                tree=tree,
                syntax_error=None,
                filename=filename,
                source_code=source_code
            )
        except SyntaxError as exc:
            logger.debug(f"Syntax error detected while parsing {filename}: {exc}")
            return ParseResult(
                success=False,
                tree=None,
                syntax_error=exc,
                filename=filename,
                source_code=source_code
            )

    @classmethod
    def parse_file(
        cls,
        file_path: Union[str, Path],
        relative_path: Optional[str] = None
    ) -> ParseResult:
        """
        Reads a file from disk and parses its AST.
        Captures read/encoding errors as well as parser syntax errors.
        """
        path = Path(file_path)
        display_name = relative_path or str(path)

        try:
            source_code, encoding = cls.read_source_file(path)
        except UnicodeDecodeError as e:
            # Construct a SyntaxError representing the encoding failure
            err = SyntaxError(f"Encoding error: {str(e)}")
            err.filename = display_name
            err.lineno = 1
            err.offset = 1
            err.text = ""
            return ParseResult(
                success=False,
                tree=None,
                syntax_error=err,
                filename=display_name,
                source_code="",
                encoding="unsupported"
            )
        except Exception as e:
            err = SyntaxError(f"Failed to read file: {str(e)}")
            err.filename = display_name
            err.lineno = 1
            err.offset = 1
            err.text = ""
            return ParseResult(
                success=False,
                tree=None,
                syntax_error=err,
                filename=display_name,
                source_code="",
                encoding="unknown"
            )

        result = cls.parse_source(source_code, filename=display_name)
        result.encoding = encoding
        return result
