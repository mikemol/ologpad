# src/dsl_parser/grammar/transformer.py
"""
Transforms a grammar represented by an AST into Chomsky Normal Form (CNF).
"""
import itertools
from collections import defaultdict
from typing import List, Dict, Set

from ..core.ast import ASTNode

# Type alias for the internal grammar dictionary format
SimpleGrammar = Dict[str, List[List[str]]]

class CNFTransformer:
    """
    A class to perform EBNF to CNF transformation on a grammar AST.
    """
    def __init__(self, grammar_ast: List[ASTNode]):
        self._rule_counter: int = 0
        self.grammar: SimpleGrammar = self._ast_to_dict(grammar_ast)
        self.terminals: Set[str] = self._find_terminals()
        self.start_symbol: str = grammar_ast[0].children[0].value if grammar_ast else ""

    def transform(self) -> SimpleGrammar:
        """Executes the full CNF transformation pipeline."""
        print("Starting CNF transformation pipeline...")
        self._eliminate_epsilon()
        self._eliminate_units()
        self._isolate_terminals()
        self._binarize()
        print("✅ CNF transformation complete.")
        return self.grammar

    def _eliminate_epsilon(self):
        """Finds all nullable rules and eliminates them."""
        print("Step 2: Eliminating epsilon productions...")
        nullable: Set[str] = set()
        while True:
            newly_added = False
            for head, productions in self.grammar.items():
                if head in nullable: continue
                for prod in productions:
                    if not prod:
                        nullable.add(head)
                        newly_added = True
                        break
                    if all(s in nullable for s in prod):
                        nullable.add(head)
                        newly_added = True
                        break
            if not newly_added: break
        
        new_productions: SimpleGrammar = defaultdict(list)
        for head, productions in self.grammar.items():
            for prod in productions:
                nullable_indices = [i for i, s in enumerate(prod) if s in nullable]
                for i in range(1, len(nullable_indices) + 1):
                    for combo in itertools.combinations(nullable_indices, i):
                        new_prod = [s for j, s in enumerate(prod) if j not in combo]
                        if new_prod and new_prod not in new_productions[head]:
                             new_productions[head].append(new_prod)
        
        for head, prods in new_productions.items():
            self.grammar[head].extend(prods)

        for head in list(self.grammar.keys()):
            self.grammar[head] = [p for p in self.grammar[head] if p]

    # In class CNFTransformer:
    def _generate_new_non_terminal(self, base_name: str | None = "NT") -> str:
        """
        Generates a new, unique non-terminal name.
        Handles None for base_name as a safeguard.
        """
        prefix = base_name or "NT"
        self._rule_counter += 1
        safe_prefix = prefix.replace('?', '_opt').replace('*', '_rep').replace('+', '_plus')
        return f"{safe_prefix}_{self._rule_counter}"

    def _eliminate_units(self):
        """Removes all unit productions of the form A -> B."""
        print("Step 3: Eliminating unit productions...")
        while True:
            unit_rules = [(h, p[0]) for h, prods in self.grammar.items() for p in prods if len(p) == 1 and p[0] not in self.terminals]
            if not unit_rules:
                break
            
            for head, body in unit_rules:
                # Remove the unit production A -> B
                self.grammar[head].remove([body])
                # Add all productions of B to A
                if body in self.grammar:
                    for prod in self.grammar[body]:
                        if prod not in self.grammar[head]:
                            self.grammar[head].append(prod)

    def _isolate_terminals(self):
        """Ensures terminals appear only in rules of the form A -> 'a'."""
        print("Step 4: Isolating terminals...")
        new_rules: SimpleGrammar = {}
        for head, productions in self.grammar.items():
            for i, prod in enumerate(productions):
                if len(prod) > 1:
                    for j, symbol in enumerate(prod):
                        if symbol in self.terminals:
                            new_nt_name = f"TERM_{symbol.replace('\'', '')}"
                            if new_nt_name not in new_rules:
                                new_rules[new_nt_name] = [[symbol]]
                            self.grammar[head][i][j] = new_nt_name
        self.grammar.update(new_rules)

    def _ast_to_dict(self, grammar_ast: List[ASTNode]) -> Dict[str, List[List[str]]]:
        print("INFO: Converting grammar AST to internal dictionary representation...")
        grammar_dict: Dict[str, List[List[str]]] = {} # Explicitly type the local variable
        for rule_node in grammar_ast:
            if rule_node.term_type != 'Rule': continue
            
            lhs_node = rule_node.children[0]
            rule_name = lhs_node.value
            
            # We pass the specifically-typed grammar_dict to the helper
            grammar_dict[rule_name] = self._parse_rhs_node(rule_node.children[1].children[0], grammar_dict)
            
        return grammar_dict

    def _parse_rhs_node(self, node: ASTNode, grammar: Dict[str, List[List[str]]]) -> List[List[str]]:
        """
        Recursively parses the RHS of a rule, expanding EBNF operators
        and creating new rules as needed.
        """
        # Base cases: these nodes represent single symbols
        if node.term_type in ('Identifier', 'Literal'):
            return [[node.value]]
        if node.term_type == 'HexLiteral':
            return [[f"#x{node.value}"]]
        if node.term_type == 'CharRange':
            start, end = node.children[0].value, node.children[1].value
            return [[f"[#x{start}-#x{end}]"]]

        # Recursive cases: these nodes define structure
        if node.term_type == 'Choice':
            productions: List[List[str]] = []
            for child in node.children:
                productions.extend(self._parse_rhs_node(child, grammar))
            return productions
        
        if node.term_type == 'Sequence':
            return [ [item for sublist in [self._parse_rhs_node(child, grammar)[0] for child in node.children] for item in sublist] ]

        # EBNF Operator Cases: These create new rules
        if node.term_type in ('Optional', 'Repetition', 'RepetitionPlus'): # Handles ?, *, +
            base_name = node.children[0].flatten()
            new_nt_name = self._generate_new_non_terminal(base_name)
            
            # Get the inner expression (e.g., the 'A' in 'A?')
            inner_production = self._parse_rhs_node(node.children[0], grammar)
            
            if node.term_type == 'Optional': # For '?'
                grammar[new_nt_name] = inner_production + [[]] 
            else: # For '*' and '+'
                grammar[new_nt_name] = [prod + [new_nt_name] for prod in inner_production] + [[]]
            
            if node.term_type == 'RepetitionPlus': # For '+'
                # A+ is equivalent to A A*, so we return the inner expression
                # followed by the new repetition rule.
                return [[p[0], new_nt_name] for p in inner_production]

            return [[new_nt_name]]

        raise TypeError(f"Unknown AST node type in RHS: {node.term_type}")

    def _find_terminals(self) -> Set[str]:
        """Scans the grammar to find all terminal symbols."""
        # By adding the type annotation here, Pylance knows this is a set of strings
        terminals: Set[str] = set()
        
        for productions in self.grammar.values():
            for prod in productions:
                for symbol in prod:
                    terminals.add(symbol)
        return terminals

    def _binarize(self):
        """Converts rules with more than 2 symbols into a chain of binary rules."""
        print("Step 5: Binarizing long rules...")
        for head in list(self.grammar.keys()):
            # Using a while loop is safe for in-place modification
            i = 0
            while i < len(self.grammar[head]):
                prod = self.grammar[head][i]
                if len(prod) > 2:
                    # Remove the original long production before adding the new chain
                    self.grammar[head].pop(i)
                    current_head = head
                    # Create the chain of intermediate rules
                    for j in range(len(prod) - 2):
                        new_nt = self._generate_new_non_terminal(base_name=f"{head}_BIN")
                        self.grammar.setdefault(current_head, []).append([prod[j], new_nt])
                        current_head = new_nt
                    # Terminate the chain with the final two symbols
                    self.grammar.setdefault(current_head, []).append(prod[-2:])
                else:
                    # Only advance if we didn't pop the current item
                    i += 1

if __name__ == '__main__':
    # This block demonstrates how the transformer would be used.
    print("--- CNF Transformer Demonstration ---")

    # 1. We would load a full grammar AST (bootstrap + unicode + user)
    # For now, we create a dummy ASTNode list.
    dummy_rule = ASTNode('Rule', children=[
        ASTNode('Identifier', value='Assign'),
        ASTNode('Definition', children=[
            ASTNode('Sequence', children=[
                ASTNode('Identifier', value='ID'),
                ASTNode('Literal', value='='),
                ASTNode('Identifier', value='Expr'),
                ASTNode('Literal', value=';'),
            ])
        ])
    ])
    full_grammar_ast = [dummy_rule]

    # 2. Initialize and run the transformer
    # NOTE: The current skeleton has a simplified _ast_to_dict method.
    # transformer = CNFTransformer(full_grammar_ast)
    # cnf_grammar = transformer.transform()
    
    print("\n(Note: Full implementation of steps 1-3 is required for a complete run)")
    print("Transformer skeleton is ready.")
