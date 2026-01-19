from dataclasses import dataclass
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_random

from textwrap import dedent
import json
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, TypeAdapter, ValidationError

from markdown_index.chat import LLMChat
from markdown_index.utils import extract_json_object


class TextSummarySchema(BaseModel):
    """Schema for `text_summary` and `doc_summary` LLM responses."""

    model_config = ConfigDict(extra="forbid", strict=True)

    summary: StrictStr


class TextKeywordSchema(BaseModel):
    """Schema for a single keyword object returned by the LLM."""

    model_config = ConfigDict(extra="forbid", strict=True)

    keyword: StrictStr
    synonyms: list[StrictStr]


class RetrieveIndexSchema(BaseModel):
    """Schema for `retrieve_index` LLM response."""

    model_config = ConfigDict(extra="forbid", strict=True)

    related_block_ids: list[StrictInt]


class RetrieveBlockItemSchema(BaseModel):
    """Schema for a single retrieved block item returned by the LLM."""

    model_config = ConfigDict(extra="forbid", strict=True)

    block_id: StrictInt
    related_text: StrictStr


_TEXT_KEYWORDS_ADAPTER = TypeAdapter(list[TextKeywordSchema])
_RETRIEVE_BLOCK_ADAPTER = TypeAdapter(list[RetrieveBlockItemSchema])


class TextSummaryPromptTemplate:
    def __call__(self, content: str, n_words: int) -> str:
        raise NotImplementedError()


class DocSummaryPromptTemplate:
    def __call__(self, index: str, n_words: int) -> str:
        raise NotImplementedError()

class TextKeywordsPromptTemplate:
    def __call__(self, content: str, doc_info: str = None) -> str:
        raise NotImplementedError()

class RetrieveIndexPromptTemplate:
    def __call__(self, query: str, index: str) -> str:
        raise NotImplementedError()

class RetrieveBlockPromptTemplate:
    def __call__(self, query: str, block_list: str) -> str:
        raise NotImplementedError()


@dataclass
class Templates:
    text_summary_prompt_template: TextSummaryPromptTemplate
    doc_summary_prompt_template: DocSummaryPromptTemplate
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

        self.doc_summary = retry(
            stop=stop_after_attempt(self.max_retry), 
            wait=wait_random(min=1, max=self.wait_time)
        )(self._doc_summary)
        
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

    def _text_summary(self, content: str, n_summary_words: int) -> TextSummarySchema:
        # Content is short, do not summary
        if len(content) <= n_summary_words:
            return TextSummarySchema(summary=content)
        prompt = self.templates.text_summary_prompt_template(content, n_summary_words)
        result = extract_json_object(self.chat(prompt))
        
        # Validate schema
        try:
            parsed = TextSummarySchema.model_validate(result)
        except ValidationError as e:
            raise ValueError(f"Invalid schema for text_summary: {e}") from e
        
        return parsed

    def _doc_summary(self, index: str, n_summary_words: int) -> TextSummarySchema:
        prompt = self.templates.doc_summary_prompt_template(index, n_summary_words)
        result = extract_json_object(self.chat(prompt))
        
        # Validate schema
        try:
            parsed = TextSummarySchema.model_validate(result)
        except ValidationError as e:
            raise ValueError(f"Invalid schema for doc_summary: {e}") from e
        
        return parsed

    def _text_keywords(self, content: str, doc_info: str = None) -> list[TextKeywordSchema]:
        prompt = self.templates.text_keywords_prompt_template(content, doc_info)
        keywords = extract_json_object(self.chat(prompt), is_list=True)
        
        # Validate schema
        try:
            keyword_models = _TEXT_KEYWORDS_ADAPTER.validate_python(keywords)
        except ValidationError as e:
            raise ValueError(f"Invalid schema for text_keywords: {e}") from e
        
        for keyword_obj in keyword_models:
            all_synonys = [keyword_obj.keyword] + list(keyword_obj.synonyms)
            deduplicated_synonys = []
            for synonym in all_synonys:
                is_duplicate = False
                for deduplicated_synonym in deduplicated_synonys:
                    if (deduplicated_synonym in synonym):
                        is_duplicate = True
                        break
                if not is_duplicate:
                    deduplicated_synonys.append(synonym)
            deduplicated_synonys.remove(keyword_obj.keyword)
            keyword_obj.synonyms = deduplicated_synonys
        return keyword_models


    def _retrieve_index(self, query: str, index: List[Dict[str, Any]]) -> RetrieveIndexSchema:
        prompt = self.templates.retrieve_index_prompt_template(
            query, json.dumps(index, ensure_ascii=False, indent=2)
        )
        result = extract_json_object(self.chat(prompt), is_list=False)
        
        # Validate schema
        try:
            parsed = RetrieveIndexSchema.model_validate(result)
        except ValidationError as e:
            raise ValueError(f"Invalid schema for retrieve_index: {e}") from e
        
        return parsed


    def _retrieve_block(self, query: str, block_list: list[Dict[str, Any]]) -> list[RetrieveBlockItemSchema]:
        prompt = self.templates.retrieve_block_prompt_template(
            query, json.dumps(block_list, ensure_ascii=False, indent=2)
        )
        result = extract_json_object(self.chat(prompt), is_list=True)
        
        # Validate schema
        try:
            items = _RETRIEVE_BLOCK_ADAPTER.validate_python(result)
        except ValidationError as e:
            raise ValueError(f"Invalid schema for retrieve_block: {e}") from e
        
        return items

