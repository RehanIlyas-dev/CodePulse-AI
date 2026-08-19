from app.schemas.scan import AIAnalysisResult


def format_analysis_report(title: str, language: str, ast_metrics: dict, ai: AIAnalysisResult) -> str:
    """Builds a human-readable plain-text report from the structured analysis."""
    issues = ai.issues or []
    lines = [
        "=" * 48,
        "CODE PULSE - CODE ANALYSIS REPORT",
        "=" * 48,
        "",
        f"Title    : {title}",
        f"Language : {language}",
        "",
        "-" * 48,
        "STATISTICS",
        "-" * 48,
        f"Lines of code        : {ast_metrics.get('total_lines', ast_metrics.get('lines_of_code', 0))}",
        f"Functions            : {ast_metrics.get('function_count', 0)}",
        f"Classes              : {ast_metrics.get('class_count', 0)}",
        f"Cyclomatic complexity: {ast_metrics.get('cyclomatic_complexity', 0)}",
        "",
        "-" * 48,
        "COMPLEXITY",
        "-" * 48,
        f"Time complexity  : {ai.time_complexity}",
        f"Space complexity : {ai.space_complexity}",
        "",
        "-" * 48,
        "SCORES (0-100)",
        "-" * 48,
        f"Security score        : {ai.security_score}",
        f"Maintainability score : {ai.maintainability_score}",
        "",
    ]

    if issues:
        lines += ["-" * 48, f"ISSUES FOUND ({len(issues)})", "-" * 48]
        for i, issue in enumerate(issues, 1):
            location = f" (line {issue.line_number})" if issue.line_number else ""
            lines.append(f"[{i}] {issue.type.upper()}{location}")
            lines.append(f"    Description: {issue.description}")
            lines.append(f"    Suggestion : {issue.suggestion}")
            lines.append("")
    else:
        lines += ["ISSUES FOUND: None - code looks clean.", ""]

    lines += ["-" * 48, "REFACTORED CODE", "-" * 48, ai.refactored_code, ""]

    return "\n".join(lines)
