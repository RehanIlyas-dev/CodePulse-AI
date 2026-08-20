from typing import Dict, Any

class DependencyGraphBuilder:
    @staticmethod
    def build_graph(parsed_project: Dict[str, Any]) -> Dict[str, Any]:
        files = parsed_project["files"]
        graph = {}

        for file_path, data in files.items():
            dependencies = []
            file_imports = data["imports"]

            # Map import strings to target files in project
            for other_file in files.keys():
                if file_path == other_file:
                    continue
                module_name = other_file.split(".")[0].replace("/", ".")
                for imp in file_imports:
                    if module_name in imp:
                        dependencies.append(other_file)
                        break

            graph[file_path] = dependencies

        return {
            "summary": parsed_project["summary"],
            "dependency_graph": graph,
            "files": {
                f_path: {
                    "language": details["language"],
                    "metrics": details["metrics"]
                }
                for f_path, details in files.items()
            }
        }