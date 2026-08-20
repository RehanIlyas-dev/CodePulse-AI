import os
from pathlib import Path
from typing import Dict, List, Any
from app.services.tree_sitter_engine import UniversalTreeSitterEngine

class ProjectParser:
    IGNORED_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist"}
    SUPPORTED_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".cpp": "cpp",
        ".c": "c",
        ".java": "java"
    }

    @classmethod
    def parse_repository(cls, root_dir: Path) -> Dict[str, Any]:
        file_metrics = {}
        total_loc = 0
        total_functions = 0
        total_complexity = 0

        for current_root, dirs, files in os.walk(root_dir):
            # Prune ignored folders in-place
            dirs[:] = [d for d in dirs if d not in cls.IGNORED_DIRS]

            for file in files:
                ext = Path(file).suffix.lower()
                if ext in cls.SUPPORTED_EXTENSIONS:
                    file_path = Path(current_root) / file
                    relative_path = str(file_path.relative_to(root_dir))
                    language = cls.SUPPORTED_EXTENSIONS[ext]

                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            code_content = f.read()

                        # 100% Tree-sitter execution on disk
                        ast_result = UniversalTreeSitterEngine.analyze(code_content, language)
                        
                        file_metrics[relative_path] = {
                            "language": language,
                            "metrics": ast_result,
                            "imports": cls._extract_imports(code_content, language)
                        }

                        total_loc += ast_result["total_lines"]
                        total_functions += ast_result.get("function_count", 0)
                        total_complexity += ast_result.get("cyclomatic_complexity", 1)

                    except Exception:
                        continue

        return {
            "files": file_metrics,
            "summary": {
                "total_files": len(file_metrics),
                "total_loc": total_loc,
                "total_functions": total_functions,
                "average_complexity": round(total_complexity / max(len(file_metrics), 1), 2)
            }
        }

    @staticmethod
    def _extract_imports(code: str, language: str) -> List[str]:
        """Simple line-level import extractor for dependency mapping."""
        imports = []
        lines = code.splitlines()
        for line in lines:
            line_str = line.strip()
            if language == "python" and (line_str.startswith("import ") or line_str.startswith("from ")):
                imports.append(line_str)
            elif language in ["javascript", "typescript"] and ("import " in line_str or "require(" in line_str):
                imports.append(line_str)
        return imports