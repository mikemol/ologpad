# src/dsl_parser/core/ast.py
"""
Defines the core Abstract Syntax Tree (AST) Node class for the parser.

This class is the fundamental data structure used throughout the parsing process.
It represents a "Symbol" in the unified parsing model, capable of being a
primitive (like a character) or a composite structure (like a token or rule).
"""
from typing import Any, List, Optional

class ASTNode:
    """A node in the Abstract Syntax Tree."""
    def __init__(self, term_type: str, value: Any = None, children: Optional[List['ASTNode']] = None):
        """
        Initializes an AST node.

        Args:
            term_type: The type of the terminal or non-terminal rule this
                       node represents (e.g., 'Identifier', 'Rule', 'a').
            value: The direct value of the node, if it's a leaf or has a simple
                   token value. Defaults to None.
            children: A list of child ASTNode objects. Defaults to an empty list.
        """
        self.term_type: str = term_type
        self.value: Any = value
        self.children: List['ASTNode'] = children if children else []

    def __repr__(self, level: int = 0) -> str:
        """Provides an indented, tree-like string representation for debugging."""
        indent = "  " * level
        # Display the value if it's not None
        value_str = f", value='{self.value}'" if self.value is not None else ""
        
        ret = f"{indent}ASTNode(type='{self.term_type}'{value_str})\n"
        
        for child in self.children:
            ret += child.__repr__(level + 1)
        return ret

    def flatten(self) -> str:
        """
        Recursively concatenates the values of this node and its children.

        Useful for getting the string representation of a composite node,
        like an Identifier composed of character nodes.

        Returns:
            The flattened string value.
        """
        # If the node has a direct value, use it.
        if self.value is not None:
            return str(self.value)
        # Otherwise, flatten its children.
        return "".join(child.flatten() for child in self.children)

if __name__ == '__main__':
    # This block demonstrates how to use the ASTNode class
    print("--- ASTNode Demonstration ---")

    # 1. Create primitive character nodes (as they would appear in the input stream)
    char_r = ASTNode(term_type='r', value='r')
    char_u = ASTNode(term_type='u', value='u')
    char_l = ASTNode(term_type='l', value='l')
    char_e = ASTNode(term_type='e', value='e')

    # 2. Create a composite "Identifier" node that "boxes" the character nodes
    #    Note that the parent node itself has no direct 'value'.
    id_node = ASTNode(term_type='Identifier', children=[char_r, char_u, char_l, char_e])

    # 3. Create a higher-level "Rule" node
    rule_node = ASTNode(term_type='Rule', children=[id_node])

    print("\nFull AST representation of the 'Rule' node:")
    print(rule_node)

    print("\nFlattened value of the 'Identifier' sub-node:")
    # The flatten method allows us to easily recover the original string
    flattened_id = id_node.flatten()
    print(f"'{flattened_id}'")
    
    assert flattened_id == "rule"
    print("\n✅ Demonstration complete.")
    