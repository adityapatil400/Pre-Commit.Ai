import io
import zipfile
import pytest
from backend.app.schemas.analysis_schema import (
    FindingSchema,
    SeverityEnum,
    CategoryEnum,
    ApprovalStatusEnum,
)
from backend.app.services.file_service import FileService, FileServiceError
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.fix_service import FixService
from backend.app.services.github_service import GitHubService, GitHubServiceError

def test_file_service_single_file_extraction():
    content = b"x = 42\nprint(x)\n"
    res = FileService.extract_single_python_file("sample.py", content)
    assert "sample.py" in res
    assert res["sample.py"] == "x = 42\nprint(x)\n"

def test_file_service_zip_extraction():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("app/main.py", "def main(): pass\n")
        z.writestr("README.md", "# Ignore me")
        z.writestr("app/__pycache__/main.cpython-313.pyc", "binary")

    res = FileService.extract_zip_archive(buffer.getvalue())
    assert len(res) == 1
    assert any("main.py" in k for k in res.keys())

def test_file_service_empty_zip_raises_error():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("README.md", "# No python files here")

    with pytest.raises(FileServiceError):
        FileService.extract_zip_archive(buffer.getvalue())

def test_file_service_patched_zip_creation():
    files = {"test.py": "print('fixed')\n"}
    zip_buffer = FileService.create_patched_zip(files)
    assert zip_buffer is not None
    with zipfile.ZipFile(zip_buffer) as z:
        assert "test.py" in z.namelist()
        assert z.read("test.py").decode("utf-8") == "print('fixed')\n"

def test_analysis_service_workflow():
    files = {
        "bad_script.py": "def test(a=[]):\n    pass\n"
    }
    result = AnalysisService.analyze_files(
        files_content=files,
        project_name="demo-pkg",
        source_type="zip",
        source_reference="archive.zip"
    )

    assert result.session_id is not None
    assert result.project_name == "demo-pkg"
    assert result.files_scanned == 1
    assert result.metrics.total_issues >= 1

    # Verify session is saved in FileService
    session = FileService.get_session(result.session_id)
    assert session is not None
    assert session["project_name"] == "demo-pkg"

    # Verify report generation
    report = AnalysisService.generate_session_report(result.session_id)
    assert report is not None
    assert "# PreCommit AI (LeakGuard) Analysis Report" in report

def test_fix_service_application():
    original_files = {
        "example.py": "try:\n    x = 1 / 0\nexcept:\n    pass\n"
    }
    findings = [
        FindingSchema(
            id="find-1",
            rule_id="PY-BUG-002",
            title="Bare except",
            severity=SeverityEnum.WARNING,
            category=CategoryEnum.BUG,
            file_path="example.py",
            line=3,
            column=1,
            description="Bare except clause",
            code_snippet="except:",
            suggested_fix="except Exception:",
            explanation="Avoid bare except",
            is_potential_warning=False,
            fixable=True,
            original_code="except:\n",
            proposed_code="except Exception:\n",
            unified_diff="",
            approval_status=ApprovalStatusEnum.ACCEPTED,
        )
    ]

    patched = FixService.apply_approved_fixes(original_files, findings)
    assert "except Exception:" in patched["example.py"]
    assert "except:\n" not in patched["example.py"]

def test_github_service_url_parsing():
    owner, repo = GitHubService.parse_repo_url("https://github.com/torvalds/linux")
    assert owner == "torvalds"
    assert repo == "linux"

    with pytest.raises(GitHubServiceError):
        GitHubService.parse_repo_url("https://gitlab.com/invalid/url")
