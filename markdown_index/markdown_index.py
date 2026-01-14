from typing import Self, Optional, List, Dict, Tuple, Any

import logging
logger = logging.getLogger(__name__)

import concurrent.futures

import json
import numpy as np

from tokenizers import Tokenizer

from markdown_index.utils import get_tokenizer, get_table_ranges
from markdown_index.chat import LLMChat
from markdown_index.llm_ops.base import LLMOps, get_templates


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

    def full_title(self):
        title = self.title.lstrip("#")
        if self.parent is not None:
            title = self.parent.full_title() + " > " + title.lstrip("#")
        return title
    
    def set_summary(self, summary: str):
        self.summary = summary


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
                if self._count_tokens("\n".join(markdown_lines[start_line:i])) > max_tokens_per_node:
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

        return splitted_nodes


    # If we wanna split some "heavy" nodes
    if max_tokens_per_node is not None:
        splitted_nodes: Dict[MarkdownNode, List[MarkdownNode]] = {}
        for node in nodes:
            # If the node text is within the limit, continue
            if self._count_tokens(node.text) <= max_tokens_per_node:
                continue
            splitted_nodes[node] = split_node(node)

        for full_node in splitted_nodes:
            parent_node_idx = nodes.index(full_node)
            for idx, splitted_node in enumerate(splitted_nodes[full_node]):
                nodes.insert(parent_node_idx + idx + 1, splitted_node)
            nodes.remove(full_node)  # Delete the "full node"
        
        if nodes[-1].is_forced_split:  # Split will add an extra "\n" to the last node
            nodes[-1].text = nodes[-1].text.removesuffix("\n")

    return nodes


def improve_table_split(markdown_content: str, nodes: List[MarkdownNode], table_ranges: List[Tuple[int, int]] = None) -> List[MarkdownNode]:
    table_ranges = table_ranges or get_table_ranges(markdown_content)
    for i, node in enumerate(nodes):
        # Check if any node contains splitted table
        for table_start, table_end in table_ranges:
            # The node only contains part of the table (the header is missed!)
            if node.line_start > table_start and node.line_start < table_end:
                # The header first line is in the previous node, i.e.,
                # | col1 | col2 | col3 |
                if node.line_start == table_start + 1:
                    table_first_line = nodes[i-1].text.split("\n")[-1] + "\n"
                    node.text = table_first_line + node.text
                    nodes[i-1].text = nodes[i-1].text.removesuffix(table_first_line)
                # Previous node only contain the first two lines of the table, i.e.,
                # | col1 | col2 | col3 |
                # |------|------|------|
                elif node.line_start == table_start + 2:
                    table_first_two_lines = "\n".join(nodes[i-1].text.split("\n")[-2:]) + "\n"
                    node.text = table_first_two_lines + node.text
                    nodes[i-1].text = nodes[i-1].text.removesuffix(table_first_two_lines)
                # Previous node also contains some of the table's main body
                # Just copy the table header to the next node
                else:
                    table_first_two_lines = "\n".join(nodes[i-1].text.split("\n")[-2:]) + "\n"
                    node.text = table_first_two_lines + node.text
                # One node could only miss one table header
                break

    return nodes


def nodes2json(nodes: List[MarkdownNode]) -> str:
    node_to_idx = {node: i for i, node in enumerate(nodes)}
    nodes_data = []
    for node in nodes:
        parent_idx = node_to_idx.get(node.parent, -1) if node.parent else -1
        nodes_data.append({
            "title": node.title,
            "line_start": node.line_start,
            "line_end": node.line_end,
            "text": node.text,
            "parent_idx": parent_idx,
            "is_forced_split": node.is_forced_split,
            "summary": node.summary
        })
    return json.dumps(nodes_data, ensure_ascii=False, indent=2)


def json2nodes(json_str: str) -> List[MarkdownNode]:
    nodes_data = json.loads(json_str)
    nodes = []
    # First pass: create nodes
    for data in nodes_data:
        node = MarkdownNode(
            title=data["title"],
            line_start=data["line_start"],
            line_end=data["line_end"],
            text=data["text"],
            parent=None,
            is_forced_split=data["is_forced_split"]
        )
        node.summary = data.get("summary")
        nodes.append(node)
    
    # Second pass: link parents
    for i, data in enumerate(nodes_data):
        parent_idx = data["parent_idx"]
        if parent_idx != -1:
            if 0 <= parent_idx < len(nodes):
                nodes[i].parent = nodes[parent_idx]
            else:
                logging.warning(f"Parent index {parent_idx} out of bounds for node {i}")

    return nodes


class MarkdownIndex:
    def __init__(
        self,

        markdown_content: str,
        
        openai_model_name: str,
        openai_base_url: str,
        openai_api_key: str,
        openai_timeout: float = 1000,
        llm_parallel_workers: int = 10,

        tokenizer: str = "default",
        language: str = "en",

        index_json: str = None,
        max_tokens_per_node: Optional[int]=None,
        improve_table_split: bool = True,

        summary_words: int = 50,
        approx_max_input_tokens: int = 8000,

        approx_keyword_result_size: int = 500,

        max_retry: int = 3,
        wait_time: float = 10
    ):
        self.markdown_content = markdown_content
        self.markdown_lines = markdown_content.split("\n")

        self.openai_model_name = openai_model_name
        self.openai_base_url = openai_base_url
        self.openai_api_key = openai_api_key
        self.openai_timeout = openai_timeout
        self.llm_parallel_workers = llm_parallel_workers

        self.max_tokens_per_node = max_tokens_per_node
        self.approx_max_input_tokens = approx_max_input_tokens
        self.approx_keyword_result_size = approx_keyword_result_size

        self.tokenizer = tokenizer
        self.language = language
        
        self.chat = LLMChat(
            model=self.openai_model_name,
            base_url=self.openai_base_url,
            api_key=self.openai_api_key,
            timeout=self.openai_timeout
        )

        self.llm_ops = LLMOps(
            chat=self.chat,
            templates=get_templates(self.language),
            max_retry=max_retry,
            wait_time=wait_time
        )

        logger.info("Extract table ranges...")
        self.table_ranges = get_table_ranges(self.markdown_content)
        logger.info(f"Table ranges extracted, total {len(self.table_ranges)} tables")

        if index_json is None:
            logger.info("No index_json passed, will generate index from markdown string...")
            logger.info("Start generating markdown nodes...")

            self.nodes: List[MarkdownNode] = extract_nodes(self.markdown_content, self.max_tokens_per_node, self.tokenizer)
            if self.improve_table_split:
                self.nodes = improve_table_split(self.markdown_content, self.nodes)

            logger.info(f"Node generation finished, total {len(self.nodes)} nodes")
            logger.info("Start generating index")
            node_summaries = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.llm_parallel_workers) as executor:
                futures = [
                    executor.submit(
                        self.llm_ops.retrieve_index,
                        node.full_title() + "\n" + node.text
                    ) for node in self.nodes]
                for future in futures:
                    node_summaries.append(future.result())
                for i, summary in enumerate(node_summaries):
                    self.nodes[i].set_summary(summary)

            logger.info(f"Index generation finished, number of nodes: {self._count_tokens(self.index_str)}")
        
        else:
            logger.info("Load index from json file...")
            self.nodes = json2nodes(index_json)
            logger.info(f"Index loaded, number of nodes: {len(self.nodes)}")

        logger.info("Start generating line to node mapping...")
        self.line2node: List[MarkdownNode] = []
        for node in self.nodes:
            for line in range(node.line_start, node.line_end):
                self.line2node[line] = node

    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text).ids)

    def retrieve_index(self, query: str) -> List[Dict[str, Any]]:
        n_index_segments = len(self.tokenizer.encode(self.index_str).ids) // self.index_max_part + 1
        n_nodes_per_segment = len(self.nodes) // n_index_segments + 1
        
        retrieved_ids = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.llm_parallel_workers) as executor:
            futures = [
                executor.submit(
                    self.llm_ops.retrieve_index,
                    query,
                    self.index[i*n_nodes_per_segment: (i+1) * n_nodes_per_segment]
                ) for i in range(n_index_segments)
            ]
            for future in futures:
                retrieved_ids.extend(future.result())
        
        logger.info(f"Index retrieval finished, retrieved {len(retrieved_ids)} nodes")

        return retrieved_ids

    def retrieve_block(self, query: str, block_ids: List[int]) -> List[str]:
        block_contents = [{
            "block_id": block_id,
            "full_title": self.nodes[block_id].full_title(),
            "text": self.nodes[block_id].text,
        } for block_id in block_ids]

        block_lists = []
        current_block_list = []
        for block in block_contents:
            estimated_block_list_size = self._count_tokens(json.dumps(current_block_list + [block], ensure_ascii=False, indent=2))
            if estimated_block_list_size > self.approx_max_input_tokens:
                if len(current_block_list) > 0:
                    error_message = f"Single block size exceeds the limit, block id: {current_block_list[-1]['block_id']}"
                    logger.error(error_message)
                    raise ValueError(error_message)

                block_lists.append(current_block_list)
                current_block_list = [block]
            else:
                current_block_list.append(block)
        if current_block_list:
            block_lists.append(current_block_list)

        retrieved_senteces = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.llm_parallel_workers) as executor:
            futures = [
                executor.submit(
                    self.llm_ops.retrieve_block,
                    query,
                    json.dumps(block_list, ensure_ascii=False, indent=2)
                ) for block_list in block_lists
            ]
            for future in futures:
                retrieved_senteces.extend(future.result())
        
        logger.info(f"Block retrieval finished, retrieved {len(retrieved_senteces)} sentences")

        return retrieved_senteces
    
    def _compute_match_score(self, keywords: Dict[str, Any], line: str) -> float:
        occurences = []
        for keyword in keywords:
            word = keyword["keyword"]
            synonyms = keyword["synonyms"]

            occurence = line.count(word)
            for synonym in synonyms:
                occurence += line.count(synonym) * 0.8  # We add a discount to the synonyms
            occurences.append(occurence)
        
        score = (np.mean(occurences)**0.5) * \
            (np.prod([np.sqrt(o + 1) for o in occurences])**(1/len(occurences)))
        
        # First term: total occurence score. If no occurence of any keywords, it is 0.
        # Second term: score considering different keywords. If all keywords have ocurrences, this term is large.

        return score
            

    def keyword_search(self, keywords: List[Dict[str, Any]]) -> List[int]:
        line_matching_scores = [self._compute_match_score(keywords, line) for line in self.markdown_lines]
        sorted_line_indices = np.argsort(line_matching_scores)[::-1]
        extracted_lines = [sorted_line_indices[i] for i in range(len(sorted_line_indices)) if line_matching_scores[sorted_line_indices[i]] > 0]
        extracted_nodes = [self.line2node[line] for line in extracted_lines]

        # Try to expand each line
        for line_number, node in zip(extracted_lines, extracted_nodes):
            n_expand_lines = 0
            while True:
                if line_number - n_expand_lines < node.line_start and line_number + n_expand_lines + 1 >= node.line_end:
                    break
                extracted_lines = self.markdown_lines[line_number - n_expand_lines: line_number + n_expand_lines + 1]
                if self._count_tokens("\n".join(extracted_lines)) > self.approx_max_input_tokens:
                    break
                n_expand_lines += 1
        
        # If in table and table header is not included
        