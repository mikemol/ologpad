# src/dsl_parser/utils/unicode_rules.py
"""
Generates foundational Unicode grammar rules from the Unicode Character Database.
"""
import requests
from collections import defaultdict
from typing import Dict, List, Union, Tuple

from ..core.ast import ASTNode

# --- Type Aliases for Readability ---
RangeTuple = Tuple[str, int, int]
Production = List[Union[str, RangeTuple]]
IntermediateGrammar = Dict[str, List[Production]]

def _fetch_and_process_data() -> Dict[str, List[int]]:
    """Fetches UnicodeData.txt and groups code points by General Category."""
    url = "https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Unicode data: {e}")
        return {}

    lines = response.text.strip().split('\n')
    category_map: defaultdict[str, list[int]] = defaultdict(list)

    for line in lines:
        parts = line.split(';')
        if len(parts) > 2:
            code_point_str, category = parts[0], parts[2]
            category_map[category].append(int(code_point_str, 16))
            
    return category_map

def _build_intermediate_grammar() -> IntermediateGrammar:
    """Processes raw Unicode data into a structured intermediate dictionary."""
    category_map = _fetch_and_process_data()
    if not category_map:
        return {}

    category_rules: IntermediateGrammar = {}
    for cat, codes in sorted(category_map.items()):
        if not codes: continue
        codes.sort()
        
        ranges: List[RangeTuple] = []
        start = end = codes[0]
        for code in codes[1:]:
            if code == end + 1:
                end = code
            else:
                ranges.append(('range', start, end))
                start = end = code
        ranges.append(('range', start, end))

        category_rules[f"{cat}_chars"] = [[r] for r in ranges]
    
    composite_defs = {
        "Letter": ['Lu_chars', 'Ll_chars', 'Lt_chars', 'Lm_chars', 'Lo_chars'],
        "Mark": ['Mn_chars', 'Mc_chars', 'Me_chars'],
        "Number": ['Nd_chars', 'Nl_chars', 'No_chars'],
        "Punctuation": ['Pc_chars', 'Pd_chars', 'Ps_chars', 'Pe_chars', 'Pi_chars', 'Pf_chars', 'Po_chars'],
        "Symbol": ['Sm_chars', 'Sc_chars', 'Sk_chars', 'So_chars'],
        "Separator": ['Zs_chars', 'Zl_chars', 'Zp_chars'],
    }
    
    final_grammar: IntermediateGrammar = {}
    for name, cats in composite_defs.items():
        final_grammar[name] = [[cat] for cat in cats]
    
    final_grammar.update(category_rules)
    return final_grammar

def _format_as_ast(grammar: IntermediateGrammar) -> List[ASTNode]:
    """Formats the intermediate grammar as a list of ASTNode objects."""
    ast_rules: List[ASTNode] = []
    for name, productions in grammar.items():
        choice_children: List[ASTNode] = []
        for production in productions:
            sequence_nodes: List[ASTNode] = []
            for symbol in production:
                node: ASTNode
                if isinstance(symbol, tuple):
                    _, p_start, p_end = symbol
                    if p_start == p_end:
                        node = ASTNode('HexLiteral', value=f"{p_start:04X}")
                    else:
                        node = ASTNode('CharRange', children=[
                            ASTNode('HexLiteral', value=f"{p_start:04X}"),
                            ASTNode('HexLiteral', value=f"{p_end:04X}")
                        ])
                    sequence_nodes.append(node)
                else: 
                    node = ASTNode('Identifier', value=symbol)
                    sequence_nodes.append(node)
            
            if len(sequence_nodes) == 1:
                choice_children.append(sequence_nodes[0])
            else:
                choice_children.append(ASTNode('Sequence', children=sequence_nodes))
        
        definition_node = ASTNode('Definition', children=[ASTNode('Choice', children=choice_children)])
        rule_node = ASTNode('Rule', children=[
            ASTNode('Identifier', value=name),
            definition_node
        ])
        ast_rules.append(rule_node)
    return ast_rules

def _format_as_text(grammar: IntermediateGrammar) -> str:
    """Formats the intermediate grammar as a human-readable EBNF string."""
    lines: List[str] = []
    for name, productions in grammar.items():
        body_parts: List[str] = []
        for production in productions:
            prod_str_parts: List[str] = []
            for symbol in production:
                if isinstance(symbol, tuple):
                    _, p_start, p_end = symbol
                    if p_start == p_end:
                        prod_str_parts.append(f"#x{p_start:04X}")
                    else:
                        prod_str_parts.append(f"[#x{p_start:04X}-#x{p_end:04X}]")
                else:
                    prod_str_parts.append(symbol)
            body_parts.append(" ".join(prod_str_parts))
        lines.append(f"{name:<18} ::= {' | '.join(body_parts)} ;")
    return "\n".join(lines)

def generate_unicode_ruleset(output_format: str = 'ast') -> Union[List[ASTNode], str, IntermediateGrammar]:
    """Generates foundational Unicode grammar rules."""
    intermediate_grammar = _build_intermediate_grammar()
    
    if output_format == 'ast':
        return _format_as_ast(intermediate_grammar)
    if output_format == 'text':
        return _format_as_text(intermediate_grammar)
    if output_format == 'dict':
        return intermediate_grammar
    
    raise ValueError(f"Unknown output format: '{output_format}'")

if __name__ == '__main__':
    print("--- Generating unicode_base.ebnf text file for inspection ---")
    ebnf_text = generate_unicode_ruleset(output_format='text')
    
    if isinstance(ebnf_text, str):
        try:
            with open('unicode_base.ebnf', 'w', encoding='utf-8') as f:
                f.write(ebnf_text)
            print("✅ Done. File 'unicode_base.ebnf' created.")
        except Exception as e:
            print(f"An error occurred: {e}")
