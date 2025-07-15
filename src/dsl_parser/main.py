# src/dsl_parser/main.py
"""
The main entry point for demonstrating and running the DSL parser pipeline.
"""
import pprint
from typing import List

from .core.ast import ASTNode
from .utils.unicode_rules import generate_unicode_ruleset
from .grammar.bootstrap import get_bootstrap_grammar
from .grammar.transformer import CNFTransformer, SimpleGrammar

def main():
    """Drives the grammar loading and transformation process."""
    print("--- Running Grammar Pipeline Demonstration ---")

    # --- Step 1: Load all grammar definitions as ASTs ---
    print("\n[1/4] Loading foundational Unicode rules...")
    # Generate the rules
    unicode_rules_result = generate_unicode_ruleset(output_format='ast')
    
    if not isinstance(unicode_rules_result, list):
        raise TypeError(f"Expected a list of ASTNodes, but got {type(unicode_rules_result)}")
    
    unicode_ast: List[ASTNode] = unicode_rules_result
    print(f"✅ Loaded {len(unicode_ast)} Unicode rules.")

    print("\n[2/4] Loading bootstrap grammar for EBNF...")
    bootstrap_ast: List[ASTNode] = get_bootstrap_grammar()
    print(f"✅ Loaded {len(bootstrap_ast)} bootstrap rules.")

    # --- Step 2: Combine grammars ---
    full_grammar_ast: List[ASTNode] = unicode_ast + bootstrap_ast
    print(f"\n[3/4] Combined grammars. Total rules: {len(full_grammar_ast)}.")

    # --- Step 3: Transform grammar to CNF ---
    print("\n[4/4] Initializing and running the CNF Transformer...")
    transformer = CNFTransformer(full_grammar_ast)
    
    cnf_grammar: SimpleGrammar = transformer.transform()

    # --- Step 4: Display the result ---
    print("\n--- Transformation Output ---")
    print("The following dictionary is the partially transformed grammar.")
    
    pprint.pprint(cnf_grammar)

if __name__ == '__main__':
    main()