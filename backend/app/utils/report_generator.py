from typing import Dict, Any, List, Optional

class ReportGenerator:
    """
    Generates Markdown and structured summaries for analysis results.
    """

    @staticmethod
    def generate_markdown_report(
        result_dict: Optional[Dict[str, Any]] = None,
        *,
        project_name: Optional[str] = None,
        source_type: Optional[str] = None,
        source_ref: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        findings: Optional[List[Dict[str, Any]]] = None,
        scanned_at: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        files_scanned: Optional[int] = None,
        total_lines_analyzed: Optional[int] = None
    ) -> str:
        data = result_dict or {}

        p_name = project_name or data.get("project_name", "Python Project")
        s_ref = source_ref or data.get("source_reference", "")
        m = metrics if metrics is not None else data.get("metrics", {})
        f_list: List[Dict[str, Any]] = findings if findings is not None else data.get("findings", [])
        timestamp = scanned_at or data.get("scanned_at", "")
        dur = duration_seconds if duration_seconds is not None else data.get("duration_seconds", 0)
        f_scanned = files_scanned if files_scanned is not None else data.get("files_scanned", len(data.get("files", {})))
        tot_lines = total_lines_analyzed if total_lines_analyzed is not None else data.get("total_lines_analyzed", 0)

        lines = [
            f"# PreCommit AI (LeakGuard) Analysis Report",
            f"",
            f"**Project Name:** {p_name}",
            f"**Source Reference:** {s_ref}",
            f"**Timestamp:** {timestamp}",
            f"**Duration:** {dur}s",
            f"**Files Scanned:** {f_scanned}",
            f"**Total Lines Analyzed:** {tot_lines:,}",
            f"",
            f"---",
            f"",
            f"## Summary Metrics",
            f"- **Total Issues:** {m.get('total_issues', len(f_list))}",
            f"- **Syntax Errors:** {m.get('syntax_errors', 0)}",
            f"- **Resource Leaks:** {m.get('resource_leak_warnings', 0)}",
            f"- **Memory Warnings:** {m.get('memory_warnings', 0)}",
            f"- **Bugs & Antipatterns:** {m.get('bug_warnings', 0)}",
            f"- **Informational Notices:** {m.get('information_count', 0)}",
            f"",
            f"---",
            f"",
            f"## Detailed Findings",
        ]

        if not f_list:
            lines.append("\n*No issues or warnings detected. Code looks clean!*")
        else:
            for idx, f in enumerate(f_list, 1):
                rule_id = f.get("rule_id", "PY-UNK")
                title = f.get("title", "Untitled finding")
                sev = f.get("severity", "warning").upper()
                file_loc = f"{f.get('file_path', '')}:{f.get('line', 1)}"
                status = str(f.get("approval_status", "pending")).upper()

                lines.append(f"\n### {idx}. [{rule_id}] {title}")
                lines.append(f"- **Severity:** {sev}")
                lines.append(f"- **Location:** `{file_loc}`")
                lines.append(f"- **Approval Status:** {status}")
                if f.get("description"):
                    lines.append(f"- **Description:** {f.get('description')}")
                if f.get("suggested_fix"):
                    lines.append(f"- **Suggested Fix:** {f.get('suggested_fix')}")

        return "\n".join(lines)
