from tree_sitter_language_pack import get_parser

# Per-language node type names for function-like declarations.
# Empirically verified against each grammar (sample parse + node-type dump).
FUNCTION_NODES = {
    "python": {"function_definition"},
    "javascript": {"function_declaration", "arrow_function", "method_definition", "function_expression", "generator_function_declaration"},
    "typescript": {"function_declaration", "arrow_function", "method_definition", "function_expression", "generator_function_declaration"},
    "c": {"function_definition"},
    "cpp": {"function_definition"},
    "java": {"method_declaration", "constructor_declaration"},
    "go": {"function_declaration", "method_declaration"},
    "rust": {"function_item"},
    "ruby": {"method", "singleton_method"},
    "php": {"function_definition", "method_declaration", "anonymous_function", "arrow_function"},
    "swift": {"function_declaration", "init_declaration"},
    "kotlin": {"function_declaration"},
    "csharp": {"method_declaration", "constructor_declaration", "local_function_statement"},
    "bash": {"function_definition"},
    # Verified against grammar output (branch-heavy samples)
    "lua": {"function_declaration", "function_definition"},
    "scala": {"function_definition"},
    "perl": {"subroutine_declaration_statement"},
    "r": {"function_definition"},
}

# Per-language node types that represent a branch/loop decision (cyclomatic complexity).
DECISION_NODES = {
    "python": {"if_statement", "elif_clause", "for_statement", "while_statement", "conditional_expression", "try_statement", "except_clause"},
    "javascript": {"if_statement", "for_statement", "for_in_statement", "while_statement", "do_statement", "switch_statement", "catch_clause", "conditional_expression"},
    "typescript": {"if_statement", "for_statement", "for_in_statement", "while_statement", "do_statement", "switch_statement", "catch_clause", "conditional_expression"},
    "c": {"if_statement", "for_statement", "while_statement", "do_statement", "switch_statement", "case_statement", "catch_clause", "conditional_expression"},
    "cpp": {"if_statement", "for_statement", "while_statement", "do_statement", "switch_statement", "case_statement", "catch_clause", "conditional_expression"},
    "java": {"if_statement", "for_statement", "while_statement", "do_statement", "switch_statement", "case", "catch_clause", "conditional_expression", "ternary_expression"},
    "go": {"if_statement", "for_statement", "switch_statement", "case_clause", "type_switch_statement", "select_statement"},
    "rust": {"if_expression", "if_let_expression", "match_expression", "for_expression", "while_expression", "loop_expression", "while_let_expression", "match_arm"},
    "ruby": {"if", "unless", "while", "until", "for", "case", "when", "rescue", "elsif"},
    "php": {"if_statement", "for_statement", "foreach_statement", "while_statement", "do_statement", "switch_statement", "case", "catch_clause", "conditional_expression", "ternary_expression"},
    "swift": {"if_statement", "for_statement", "while_statement", "do_statement", "switch_statement", "case", "catch_clause", "guard_statement", "ternary_expression"},
    "kotlin": {"if_expression", "when_expression", "for_statement", "while_statement", "do_while_statement", "catch_clause", "when_entry"},
    "csharp": {"if_statement", "for_statement", "foreach_statement", "while_statement", "do_statement", "switch_statement", "case", "catch_clause", "conditional_expression", "ternary_expression"},
    "bash": {"if_statement", "for_statement", "while_statement", "until_statement", "case_statement", "select_statement"},
    # Verified against grammar output (branch-heavy samples)
    "lua": {"if_statement", "for_statement", "while_statement"},
    "scala": {"if_expression", "match_expression", "case_clause"},
    "perl": {"if", "elsif", "while", "foreach", "for_statement"},
    "r": {"if_statement", "for_statement", "while_statement"},
}

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

        decision_nodes = DECISION_NODES.get(lang, DECISION_NODES.get("python"))
        function_nodes = FUNCTION_NODES.get(lang, FUNCTION_NODES.get("python"))

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