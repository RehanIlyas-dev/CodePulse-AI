from tree_sitter_language_pack import get_parser

class UniversalTreeSitterEngine:
    @classmethod
    def analyze(cls, code: str, language: str) -> dict:
        lang = language.lower().strip()
        
        try:
            parser = get_parser(lang)
            tree = parser.parse(code.encode("utf-8")) # Parse the code into a syntax tree
            root_node = tree.root_node
        except Exception:
            return {
                "language": lang,
                "supported": False,
                "total_lines": len(code.splitlines()),
                "has_syntax_errors": False,
                "cyclomatic_complexity": 1
            }
        decision_nodes = {
            "if_statement", "for_statement", "while_statement", 
            "switch_statement", "catch_clause", "elif_clause"
        }
        function_nodes = {
            "function_definition", "function_declaration", 
            "method_definition", "arrow_function"
        }

        decision_count = 0
        function_count = 0
        # Traverse the syntax tree to count decision points and functions
        def traverse(node):
            nonlocal decision_count, function_count
            if node.type in decision_nodes:
                decision_count += 1
            if node.type in function_nodes:
                function_count += 1
            for child in node.children:
                traverse(child)

        traverse(root_node)

        return {
            "language": lang,
            "supported": True,
            "total_lines": len(code.splitlines()),
            "has_syntax_errors": root_node.has_error,
            "function_count": function_count,
            "cyclomatic_complexity": decision_count + 1
        }