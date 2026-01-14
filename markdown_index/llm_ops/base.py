from dataclasses import dataclass
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_random

from textwrap import dedent
import json
from jsonschema import validate, ValidationError

from markdown_index.chat import LLMChat
from markdown_index.utils import extract_json_object


# JSON Schemas for validation
TEXT_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"}
    },
    "required": ["summary"],
    "additionalProperties": False
}

TEXT_KEYWORDS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "keyword": {"type": "string"},
            "synonyms": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["keyword", "synonyms"],
        "additionalProperties": False
    }
}

RETRIEVE_INDEX_SCHEMA = {
    "type": "object",
    "properties": {
        "related_block_ids": {
            "type": "array",
            "items": {"type": "integer"}
        }
    },
    "required": ["related_block_ids"],
    "additionalProperties": False
}

RETRIEVE_BLOCK_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "block_id": {"type": "string"},
            "related_text": {"type": "string"}
        },
        "required": ["block_id", "related_text"],
        "additionalProperties": False
    }
}


class TextSummaryPromptTemplate:
    def __call__(self, content: str, n_words: int) -> str:
        raise NotImplementedError()

class TextKeywordsPromptTemplate:
    def __call__(self, content: str) -> list[Dict[str, Any]]:
        raise NotImplementedError()

class RetrieveIndexPromptTemplate:
    def __call__(self, query: str, index: List[Dict[str, Any]]) -> list[int]:
        raise NotImplementedError()

class RetrieveBlockPromptTemplate:
    def __call__(self, query: str) -> list[str]:
        raise NotImplementedError()


@dataclass
class Templates:
    text_summary_prompt_template: TextSummaryPromptTemplate
    text_keywords_prompt_template: TextKeywordsPromptTemplate
    retrieve_index_prompt_template: RetrieveIndexPromptTemplate
    retrieve_block_prompt_template: RetrieveBlockPromptTemplate


def get_templates(language: str) -> Templates:
    if language == "cn":
        # Lazy import to avoid circular imports (`cn.py` imports `Templates`).
        from markdown_index.llm_ops.cn import cn_templates
        return cn_templates
    else:
        # Lazy import to avoid circular imports (`en.py` imports `Templates`).
        from markdown_index.llm_ops.en import en_templates
        return en_templates



class LLMOps:
    def __init__(self, 
        chat: LLMChat, 
        templates: Templates,
        max_retry: int = 3, 
        wait_time: float = 10
    ):
        self.chat = chat
        self.templates = templates
        self.max_retry = max_retry
        self.wait_time = wait_time
        
        self.text_summary = retry(
            stop=stop_after_attempt(self.max_retry), 
            wait=wait_random(min=1, max=self.wait_time)
        )(self._text_summary)
        
        self.text_keywords = retry(
            stop=stop_after_attempt(self.max_retry), 
            wait=wait_random(min=1, max=self.wait_time)
        )(self._text_keywords)

        self.retrieve_index = retry(
            stop=stop_after_attempt(self.max_retry), 
            wait=wait_random(min=1, max=self.wait_time)
        )(self._retrieve_index)

        self.retrieve_block = retry(
            stop=stop_after_attempt(self.max_retry), 
            wait=wait_random(min=1, max=self.wait_time)
        )(self._retrieve_block)


    def _text_summary(self, content: str) -> str:
        prompt = self.templates.text_summary_prompt_template(content)
        result = extract_json_object(self.chat(prompt))
        
        # Validate JSON schema
        try:
            validate(instance=result, schema=TEXT_SUMMARY_SCHEMA)
        except ValidationError as e:
            raise ValueError(f"Invalid JSON schema for text_summary: {e.message}")
        
        summary = result["summary"]
        return str(summary)

    def _text_keywords(self, content: str) -> list[Dict[str, Any]]:
        prompt = self.templates.text_keywords_prompt_template(content)
        keywords = extract_json_object(self.chat(prompt), is_list=True)
        
        # Validate JSON schema
        try:
            validate(instance=keywords, schema=TEXT_KEYWORDS_SCHEMA)
        except ValidationError as e:
            raise ValueError(f"Invalid JSON schema for text_keywords: {e.message}")
        
        for keyword_obj in keywords:
            all_synonys = [keyword_obj["keyword"]] + keyword_obj["synonyms"]
            deduplicated_synonys = []
            for synonym in all_synonys:
                is_duplicate = False
                for deduplicated_synonym in deduplicated_synonys:
                    if (deduplicated_synonym in synonym):
                        is_duplicate = True
                        break
                if not is_duplicate:
                    deduplicated_synonys.append(synonym)
            deduplicated_synonys.remove(keyword_obj["keyword"])
            keyword_obj["synonyms"] = deduplicated_synonys
        return keywords


    def _retrieve_index(self, query: List[Dict[str, Any]]) -> list[int]:
        prompt = self.templates.retrieve_index_prompt_template(
            query, json.dumps(query, ensure_ascii=False, indent=2)
        )
        result = extract_json_object(self.chat(prompt), is_list=False)
        
        # Validate JSON schema
        try:
            validate(instance=result, schema=RETRIEVE_INDEX_SCHEMA)
        except ValidationError as e:
            raise ValueError(f"Invalid JSON schema for retrieve_index: {e.message}")
        
        return result["related_block_ids"]


    def _retrieve_block(self, query: str, block_list: str) -> list[str]:
        prompt = self.templates.retrieve_block_prompt_template(
            query, json.dumps(block_list, ensure_ascii=False, indent=2)
        )
        result = extract_json_object(self.chat(prompt), is_list=True)
        
        # Validate JSON schema
        try:
            validate(instance=result, schema=RETRIEVE_BLOCK_SCHEMA)
        except ValidationError as e:
            raise ValueError(f"Invalid JSON schema for retrieve_block: {e.message}")
        
        return result

