from typing import Any, Self, Optional, List, Dict, Tuple, Union

import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass
from pydantic import BaseModel
from functools import cache
import concurrent.futures

import json
import numpy as np

from tokenizers import Tokenizer

from markdown_index.markdown_node import MarkdownNode, extract_nodes, smart_table_split
from markdown_index.utils import get_tokenizer, get_table_ranges
from markdown_index.chat import LLMChat
from markdown_index.llm_ops.base import LLMOps, get_templates



class MarkdownNodeData(BaseModel):
    title: str
    line_start: int
    line_end: int
    text: str
    parent_idx: Optional[int] = None
    is_forced_split: bool = False
    summary: Optional[str] = None


class MarkdownIndexData(BaseModel):
    markdown_content: str
    doc_summary: str
    nodes: List[MarkdownNodeData]



def nodes_to_node_data(nodes: List[MarkdownNode]) -> List[MarkdownNodeData]:
    node_to_idx = {node: i for i, node in enumerate(nodes)}
    nodes_data = []
    for node in nodes:
        parent_idx = node_to_idx.get(node.parent, -1) if node.parent else -1
        nodes_data.append(
            MarkdownNodeData(
                title=node.title,
                line_start=node.line_start,
                line_end=node.line_end,
                text=node.text,
                parent_idx=parent_idx,
                is_forced_split=node.is_forced_split,
                summary=node.summary,
            )
        )
    return nodes_data


def node_data_to_nodes(
    nodes_data: List[MarkdownNodeData],
) -> List[MarkdownNode]:
    """
    Convert serialized node data into `MarkdownNode` instances.
    """

    nodes = []
    # First pass: create nodes
    for data in nodes_data:
        if isinstance(data, MarkdownNodeData):
            data = data.model_dump()
        else:
            # Validate / coerce plain dicts into the schema we persist
            data = MarkdownNodeData.model_validate(data).model_dump()
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
        parent_idx = data.parent_idx
        if parent_idx != -1:
            if 0 <= parent_idx < len(nodes):
                nodes[i].parent = nodes[parent_idx]
            else:
                logging.warning(f"Parent index {parent_idx} out of bounds for node {i}")

    return nodes


@dataclass
class LLMConfig:
    openai_model_name: str
    openai_base_url: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_timeout: float = 1000
    parallel_requests: int = 10
    tokenizer_name: str = "default"
    approx_max_input_tokens: int = 8000


@dataclass
class IndexConfig:
    max_tokens_per_node: Optional[int]=3000
    improve_table_split: bool = True
    n_summary_words: int = 50
    approx_keyword_result_size: int = 500


@dataclass
class RetryConfig:
    max_retry: int = 3
    wait_time: float = 10


class MarkdownIndex:
    def __init__(
        self,

        markdown_content: str = None,
        index_data: Union[str, Dict[str, Any], MarkdownIndexData] = None,
        language: str = None,

        llm_config: LLMConfig = None ,
        index_config: Optional[IndexConfig] = None,
        retry_config: Optional[RetryConfig] = None,

    ):
        if markdown_content is not None and index_data is not None:
            raise ValueError("Only one of markdown_content or index_data must be provided")

        index_config = index_config or IndexConfig()
        retry_config = retry_config or RetryConfig()

        self.markdown_content = markdown_content
        
        # Inner data members
        self.doc_summary: str = None
        self.nodes: List[MarkdownNode] = None

        # Configurations
        self.llm_config = llm_config
        self.index_config = index_config
        self.retry_config = retry_config

        # 
        self.tokenizer = get_tokenizer(self.llm_config.tokenizer_name)
        self.language = language
        
        self.chat = LLMChat(
            model=self.llm_config.openai_model_name,
            base_url=self.llm_config.openai_base_url,
            api_key=self.llm_config.openai_api_key,
            timeout=self.llm_config.openai_timeout
        )

        self.llm_ops = LLMOps(
            chat=self.chat,
            templates=get_templates(self.language),
            max_retry=self.retry_config.max_retry,
            wait_time=self.retry_config.wait_time
        )

        if index_data is None:
            logger.info("No index_json passed, will generate index from markdown string...")
            logger.info("Start generating markdown nodes...")

            self.nodes: List[MarkdownNode] = extract_nodes(
                self.markdown_content,
                self.index_config.max_tokens_per_node,
                self.tokenizer,
            )
            if self.index_config.improve_table_split:
                self.nodes = smart_table_split(self.markdown_content, self.nodes)

            logger.info(f"Node generation finished, total {len(self.nodes)} nodes")
            logger.info("Start generating index")
            node_summaries = []

            def summary_worker(node: MarkdownNode):
                if node.text.strip() == node.title:
                    return ""
                elif self._count_tokens(node.text) <= self.index_config.n_summary_words:
                    return node.text.removeprefix(node.title).strip()
                else:
                    return self.llm_ops.text_summary(node.full_title() + "\n" + node.text, self.index_config.n_summary_words)

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.llm_config.parallel_requests) as executor:
                futures = [executor.submit(summary_worker, node) for node in self.nodes]
                for future in futures:
                    node_summaries.append(future.result())
                for i, summary in zip(range(len(self.nodes)), node_summaries):
                    self.nodes[i].set_summary(summary)

            self.doc_summary = self.llm_ops.doc_summary("\n".join(self.index()), self.index_config.n_summary_words)

            logger.info(f"Index generation finished, number of nodes: {len(self.nodes)}")
        
        else:
            logger.info("Load index from json file...")
            if isinstance(index_data, str):
                index_data = json.loads(index_data)
            if isinstance(index_data, dict):
                index_data = MarkdownIndexData.model_validate(index_data)
            if isinstance(index_data, MarkdownIndexData):
                self.markdown_content = index_data.markdown_content
                self.doc_summary = index_data.doc_summary
                self.nodes = node_data_to_nodes(index_data.nodes)
            else:
                raise ValueError(f"Invalid index data type: {type(index_data)}")

            logger.info(f"Index loaded, number of nodes: {len(self.nodes)}")
        
        
        self.markdown_lines = self.markdown_content.split("\n")
        logger.info("Extract table ranges...")
        self.table_ranges = get_table_ranges(self.markdown_content)
        logger.info(f"Table ranges extracted, total {len(self.table_ranges)} tables")

        logger.info("Start generating line to node mapping...")
        self.line2node: List[MarkdownNode] = [None for _ in range(len(self.markdown_lines))]
        for node in self.nodes:
            for line in range(node.line_start, node.line_end):
                self.line2node[line] = node

        logger.info(f"Index generation finished, size {self._count_tokens(json.dumps(self.index(), ensure_ascii=False, indent=2))} tokens")

    @cache
    def index(self) -> List[str]:
        return [f"ID={i} {node.full_title()}({node.summary}) {node.line_start}-{node.line_end}" for i, node in enumerate(self.nodes)]

    def serialize_index(self) -> str:
        return MarkdownIndexData(
            markdown_content=self.markdown_content,
            doc_summary=self.doc_summary,
            nodes=nodes_to_node_data(self.nodes)
        ).model_dump_json()

    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text).ids)

    def retrieve_index(self, query: str) -> List[Dict[str, Any]]:
        n_index_segments = self._count_tokens(json.dumps(self.index(), ensure_ascii=False, indent=2)) // self.llm_config.approx_max_input_tokens + 1
        n_nodes_per_segment = len(self.nodes) // n_index_segments + 1
        
        retrieved_ids = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.llm_config.parallel_requests) as executor:
            futures = [
                executor.submit(
                    self.llm_ops.retrieve_index,
                    query,
                    self.index()[i*n_nodes_per_segment: (i+1) * n_nodes_per_segment]
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
            if estimated_block_list_size > self.llm_config.approx_max_input_tokens:
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

        retrieved_texts = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.llm_config.parallel_requests) as executor:
            futures = [
                executor.submit(
                    self.llm_ops.retrieve_block,
                    query,
                    json.dumps(block_list, ensure_ascii=False, indent=2)
                ) for block_list in block_lists
            ]
            for future in futures:
                retrieved_texts.extend(future.result())
                # Append summary to the retrieve result
                retrieved_texts[-1]["summary"] = self.nodes[block_lists[-1]["block_id"]].summary
        
        logger.info(f"Block retrieval finished, retrieved {len(retrieved_texts)} sentences")

        return retrieved_texts
    
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
        extracted_nodes: List[MarkdownNode] = [self.line2node[line] for line in extracted_lines]
        extracted_blocks = []

        # Try to expand each line
        for line_number, node in zip(extracted_lines, extracted_nodes):
            n_expand_lines = 0
            while True:
                if line_number - n_expand_lines < node.line_start and line_number + n_expand_lines + 1 >= node.line_end:
                    break
                extracted_lines = self.markdown_lines[line_number - n_expand_lines: line_number + n_expand_lines + 1]
                if self._count_tokens("\n".join(extracted_lines)) > self.llm_config.approx_max_input_tokens:
                    break
                n_expand_lines += 1
                 
            # If in table and table header is not included
            for table_start, table_end in self.table_ranges:
                if line_number < table_end and line_number - n_expand_lines > table_start:
                    n_header_lines = max(line_number - n_expand_lines - table_start, 2)
                    n_header_lines = "\n".join(self.markdown_lines[table_start: table_start + n_header_lines]) + "\n"
                    extracted_lines = [n_header_lines] + extracted_lines
                    break
            
            extracted_blocks.append({
                "block_id": node.id,
                "full_title": node.full_title(),
                "summary": node.summary,
                "text": "\n".join(extracted_lines)
            })
        
        return extracted_blocks


    def search_by_index(self, query: str, n_results: int = 5):
        retrieved_ids = self.retrieve_index(query)
        retrieved_blocks = self.retrieve_block(query, retrieved_ids)
        return retrieved_blocks[:n_results]

    
    def search_by_keywords(self, query: str, n_results: int = 5):
        keywords: List[Dict[str, Any]] = self.llm_ops.text_keywords(query, self.doc_summary)
        logger.info(f"Keywords extracted: {keywords}")
        retrieved_blocks = self.keyword_search(keywords)
        return retrieved_blocks[:n_results]


    def retrieve(self, 
        query: str, 
        n_index_results: int, 
        n_keyword_results: int
    ) -> List[Dict[str, Any]]:
        if n_index_results <= 0 and n_keyword_results <= 0:
            raise ValueError("n_index_results and n_keyword_results cannot be both 0")
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            if n_index_results > 0:
                future_index = executor.submit(self.search_by_index, query, n_index_results)
            if n_keyword_results > 0:
                future_keywords = executor.submit(self.search_by_keywords, query, n_keyword_results)
                
            if n_index_results > 0:
                results['index_search_results'] = future_index.result()
            if n_keyword_results > 0:
                results['keyword_search_results'] = future_keywords.result()

        return results
