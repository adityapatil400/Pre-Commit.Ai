from typing import List, Optional
from pydantic import BaseModel, Field

class SyntaxErrorDetail(BaseModel):
    """
    Detailed information for a single syntax error detected by the Python AST parser.
    """
    file_path: str = Field(..., description="Relative or absolute path of the invalid file")
    line_number: int = Field(1, description="Line number where the syntax error occurred")
    column_number: int = Field(1, description="Column offset where the syntax error occurred")
    error_type: str = Field(..., description="Exception category: SyntaxError, IndentationError, UnexpectedEOF, etc.")
    error_message: str = Field(..., description="Human-readable parser error message")
    source_snippet: str = Field("", description="Source code line or context snippet where the error occurred")
    suggestion: str = Field("", description="Recommended correction")

class SyntaxAnalysisRequest(BaseModel):
    """
    Request payload to trigger syntax validation across a project.
    """
    project_id: Optional[str] = Field(None, description="Unique project workspace identifier")

class SyntaxAnalysisResponse(BaseModel):
    """
    Standardized response returned by POST /api/v1/analysis/syntax.
    """
    project_id: str = Field(..., description="Project workspace identifier")
    total_python_files: int = Field(0, description="Total count of discovered Python files")
    successfully_parsed_count: int = Field(0, description="Count of files parsed with zero syntax errors")
    files_with_syntax_errors_count: int = Field(0, description="Count of files with syntax errors")
    successfully_parsed_files: List[str] = Field(default_factory=list, description="List of valid Python file paths")
    files_with_syntax_errors: List[str] = Field(default_factory=list, description="List of invalid Python file paths")
    syntax_errors: List[SyntaxErrorDetail] = Field(default_factory=list, description="Detailed syntax error list")
    status: str = Field("completed", description="Overall syntax analysis status")
