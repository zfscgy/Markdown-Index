from dataclasses import dataclass

from textwrap import dedent

from tenacity import retry, stop_after_attempt, wait_random

from markdown_index.utils import LLMChat
from markdown_index.utils import extract_json_object


class TextSummaryPromptTemplate:
    def __call__(self, content: str, n_words: int) -> str:
        raise NotImplementedError()

class TextKeywordsPromptTemplate:
    def __call__(self, content: str) -> list[str]:
        raise NotImplementedError()

class RetrieveIndexPromptTemplate:
    def __call__(self, query: str, index: str) -> list[int]:
        raise NotImplementedError()

class RetrieveBlockPromptTemplate:
    def __call__(self, query: str) -> list[str]:
        raise NotImplementedError()

class RetrieveContentPromptTemplate:
    def __call__(self, query: str) -> list[str]:
        raise NotImplementedError()

@dataclass
class Templates:
    text_summary_prompt_template: TextSummaryPromptTemplate
    text_keywords_prompt_template: TextKeywordsPromptTemplate
    retrieve_index_prompt_template: RetrieveIndexPromptTemplate
    retrieve_block_prompt_template: RetrieveBlockPromptTemplate
    retrieve_content_prompt_template: RetrieveContentPromptTemplate


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

        self.retrieve_content = retry(
            stop=stop_after_attempt(self.max_retry), 
            wait=wait_random(min=1, max=self.wait_time)
        )(self._retrieve_content)

    def _text_summary(self, content: str) -> str:
        prompt = self.templates.text_summary_prompt_template(content)
        summary = extract_json_object(self.chat(prompt))["summary"]
        return str(summary)

    def _text_keywords(self, content: str) -> list[str]:
        prompt = self.templates.text_keywords_prompt_template(content)
        return self.chat(prompt).split(" ")

    def _retrieve_index(self, query: str) -> list[int]:
        prompt = self.templates.retrieve_index_prompt_template(query)


    def _retrieve_block(self, query: str) -> list[str]:
        prompt = self.templates.retrieve_block_prompt_template(query)

    def _retrieve_content(self, query: str) -> list[str]:
        prompt = self.templates.retrieve_content_prompt_template(query)
