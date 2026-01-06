from typing import Self, Optional, List, Dict, Tuple

import logging
logger = logging.getLogger(__name__)


from tokenizers.get_tokenizer import get_tokenizer, Tokenizer


class MarkdownNode:
    def __init__(
        self,
        title: str, 
        line_start: int, 
        line_end: int, 
        text: str,
        parent: Optional[Self] = None,
        is_forced_split: bool = False,
    ):
        self.title: str = title
        self.line_start: str = line_start
        self.line_end: str = line_end
        self.text: str = text
        self.parent: Optional[Self] = parent
        self.summary: Optional[str] = None

        self.level: int = (len(self.title) - len(self.title.lstrip('#'))) or None
        self.is_forced_split: bool = is_forced_split


def extract_nodes(
    markdown_content: str, 
    max_tokens_per_node: Optional[int]=None, 
    tokenizer: Tokenizer = get_tokenizer("default")
) -> list[MarkdownNode]:
    markdown_lines = markdown_content.split('\n')
    nodes: List[MarkdownNode] = []

    current_node_start = 0
    with_in_code_segment: bool = False

    for i, line in enumerate(markdown_lines):
        # If the text is inside the code segment, skip this
        if line.startswith('```'):
            with_in_code_segment = not with_in_code_segment
            continue
        if with_in_code_segment:
            continue
        # A new node is encountered
        if line.startswith('#'):
            # The previous node should be created
            nodes.append(MarkdownNode(
                # If the first line is not a header, title is None
                title=markdown_lines[current_node_start] if markdown_lines[current_node_start].startswith('#') else "Start of Document",
                line_start=current_node_start,
                line_end=i,
                text="\n".join(markdown_lines[current_node_start:i]),
            ))
            current_node_start = i
    
    # The last node
    nodes.append(MarkdownNode(
        title=markdown_lines[current_node_start],
        line_start=current_node_start,
        line_end=len(markdown_lines),
        text="\n".join(markdown_lines[current_node_start:]),
    ))

    current_parent_node = None
    for node in nodes:
        if current_parent_node is None:
            current_parent_node = node
        else:
            while (current_parent_node is not None) and (node.level <= current_parent_node.level):
                current_parent_node = current_parent_node.parent

        node.parent = current_parent_node
        current_parent_node = node

    # If we wanna split some "heavy" nodes
    if max_tokens_per_node is not None:

        def split_node(node: MarkdownNode) -> List[MarkdownNode]:
            splitted_nodes = []
            start_line = node.line_start
            while start_line < node.line_end:
                # Iterate the end-line until the node is too large
                for i in range(start_line + 1, node.line_end):
                    if len(tokenizer.encode("\n".join(markdown_lines[start_line:i])).ids) > max_tokens_per_node:
                        break
                # A single line (first line) is already too large
                if i == start_line + 1: 
                    logging.warning(f"Line {start_line} is already beyond the node limit, direct truncation is applied")
                    splitted_nodes.append(MarkdownNode(
                        title=node.title + f"(part-{len(splitted_nodes) + 1})",
                        line_start=start_line,
                        line_end=i,
                        text=tokenizer.decode(tokenizer.encode(markdown_lines[start_line]).ids[:max_tokens_per_node]),
                    ))
                    start_line = i
                else:
                    splitted_nodes.append(MarkdownNode(
                        title=node.title + f"(part-{len(splitted_nodes) + 1})",
                        line_start=start_line,
                        line_end=i - 1,
                        text="\n".join(markdown_lines[start_line:i - 1]),
                        is_forced_split=True
                    ))
                    start_line = i

            splitted_nodes.append(MarkdownNode(
                title=node.title + f"(part-{len(splitted_nodes) + 1})",
                line_start=start_line,
                line_end=node.line_end,
                text="\n".join(markdown_lines[start_line:node.line_end]),
            ))

            return splitted_nodes

        splitted_nodes: Dict[MarkdownNode, List[MarkdownNode]] = {}
        for node in nodes:
            # If the node text is within the limit, continue
            if len(tokenizer.encode(node.text).ids) <= max_tokens_per_node:
                continue
            splitted_nodes = split_node(node)

        for full_node in splitted_nodes:
            parent_node_idx = nodes.index(full_node)
            for idx, splitted_node in enumerate(splitted_nodes[full_node]):
                nodes.insert(parent_node_idx + idx + 1, splitted_node)
            nodes.remove(full_node)  # Delete the "full node"

    return nodes


def get_tables(markdown_content: str) -> List[Tuple[int, int]]:
    lines = markdown_content.split('\n')
    
    in_table: str = "no"  # header? | header | body | no
    