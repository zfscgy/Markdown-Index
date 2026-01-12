from typing import Self, Optional, List, Dict, Tuple

import logging
logger = logging.getLogger(__name__)


from tokenizers import Tokenizer
from markdown_index.utils import get_tokenizer, get_table_ranges


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

        self.level: int = (len(self.title) - len(self.title.lstrip('#'))) or 999
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
                text="\n".join(markdown_lines[current_node_start:i]) + "\n",
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
        # Where the node is in top-level
        if current_parent_node is None:
            current_parent_node = node
            continue
        else:
            # Find the actual parent node
            while (current_parent_node is not None) and (node.level <= current_parent_node.level):
                current_parent_node = current_parent_node.parent

        node.parent = current_parent_node
        current_parent_node = node


    def split_node(node: MarkdownNode) -> List[MarkdownNode]:
        splitted_nodes: List[MarkdownNode] = []
        start_line = node.line_start

        while start_line < node.line_end:
            text_overflow = False
            # Iterate the end-line until the node is too large
            # Max i = node.line_end + 1 and we use i - 1 for the current_end_index, which is at max node.line_end
            for i in range(start_line + 1, node.line_end + 1 + 1):
                current_end_index = i
                if len(tokenizer.encode("\n".join(markdown_lines[start_line:i])).ids) > max_tokens_per_node:
                    text_overflow = True
                    break
            # A single line (first line) is already too large
            if current_end_index == start_line + 1 and text_overflow: 
                logging.warning(f"Line {start_line} is already beyond the node limit, direct truncation is applied")
                splitted_nodes.append(MarkdownNode(
                    title=node.title + f"(part-{len(splitted_nodes) + 1})",
                    line_start=start_line,
                    line_end=current_end_index,
                    text=tokenizer.decode(tokenizer.encode(markdown_lines[start_line]).ids[:max_tokens_per_node]),
                    parent=node.parent,
                    is_forced_split=True,
                ))
                start_line = current_end_index
            else:
                splitted_nodes.append(MarkdownNode(
                    title=node.title + f"(part-{len(splitted_nodes) + 1})",
                    line_start=start_line,
                    line_end=current_end_index - 1,
                    text="\n".join(markdown_lines[start_line:current_end_index - 1]) + "\n",
                    parent=node.parent,
                    is_forced_split=True
                ))
                start_line = current_end_index - 1

        splitted_nodes[-1].text = splitted_nodes[-1].text.removeprefix("\n")

        return splitted_nodes


    # If we wanna split some "heavy" nodes
    if max_tokens_per_node is not None:
        splitted_nodes: Dict[MarkdownNode, List[MarkdownNode]] = {}
        for node in nodes:
            # If the node text is within the limit, continue
            if len(tokenizer.encode(node.text).ids) <= max_tokens_per_node:
                continue
            splitted_nodes[node] = split_node(node)

        for full_node in splitted_nodes:
            parent_node_idx = nodes.index(full_node)
            for idx, splitted_node in enumerate(splitted_nodes[full_node]):
                nodes.insert(parent_node_idx + idx + 1, splitted_node)
            nodes.remove(full_node)  # Delete the "full node"

    return nodes


def improve_table_split(markdown_content: str, nodes: List[MarkdownNode]) -> List[MarkdownNode]:
    tables = get_table_ranges(markdown_content)
    for i, node in enumerate(nodes):
        # Check if any node contains splitted table
        for table_start, table_end in tables:
            # The node only contains part of the table (the header is missed!)
            if node.line_start > table_start and node.line_start < table_end:
                # The header first line is in the previous node, i.e.,
                # | col1 | col2 | col3 |
                if node.line_start == table_start + 1:
                    table_first_line = nodes[i-1].split("\n")[-1] + "\n"
                    node.text = table_first_line + node.text
                    nodes[i-1].text = nodes[i-1].text.removesuffix(table_first_line)
                # Previous node only contain the first two lines of the table, i.e.,
                # | col1 | col2 | col3 |
                # |------|------|------|
                elif node.line_start == table_start + 2:
                    table_first_two_lines = "\n".join(nodes[i-1].split("\n")[-2:]) + "\n"
                    node.text = table_first_two_lines + node.text
                    nodes[i-1].text = nodes[i-1].text.removesuffix(table_first_two_lines)
                # Previous node also contains some of the table's main body
                # Just copy the table header to the next node
                else:
                    table_first_two_lines = "\n".join(nodes[i-1].split("\n")[-2:]) + "\n"
                    node.text = table_first_two_lines + node.text
                # One node could only miss one table header
                break

    return nodes
