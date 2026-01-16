import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

import json

from markdown_index.markdown_index import IndexConfig, MarkdownIndex, LLMConfig


def test__indexing():
    markdown_content = open("tests/data/中华人民共和国国内生产总值.md", "r", encoding="utf-8").read()
    index = MarkdownIndex(
        markdown_content,
        llm_config=LLMConfig(openai_model_name="google/gemini-3-flash-preview"),
        language="cn",
    )
    print(index.serialize_index())

    markdown_content = open("tests/data/中华人民共和国刑法.md", "r", encoding="utf-8").read()
    index = MarkdownIndex(
        markdown_content,
        llm_config=LLMConfig(openai_model_name="google/gemini-3-flash-preview"),
        language="cn",
    )
    print(index.serialize_index())

    markdown_content = open("tests/data/Survey-of-Chatbots.md", "r", encoding="utf-8").read()
    index = MarkdownIndex(
        markdown_content,
        llm_config=LLMConfig(openai_model_name="google/gemini-3-flash-preview"),
        language="en",
    )
    print(index.serialize_index())


def test__save_and_load():
    markdown_content = open("tests/data/中华人民共和国刑法.md", "r", encoding="utf-8").read()
    index = MarkdownIndex(
        markdown_content,
        llm_config=LLMConfig(openai_model_name="google/gemini-3-flash-preview"),
        index_config=IndexConfig(n_summary_words=20),
        language="cn",
    )
    serialized_index = index.serialize_index()
    print(json.dumps(index.index, ensure_ascii=False, indent=2))

    index_recovered = MarkdownIndex(
        markdown_content,
        llm_config=LLMConfig(openai_model_name="google/gemini-3-flash-preview"),
        index_json=serialized_index,
        language="cn",
    )
    serialized_json = index_recovered.serialize_index()
    with open("tests/data/中华人民共和国刑法__index.json", "w", encoding="utf-8") as f:
        f.write(serialized_json)


if __name__ == "__main__":
    test__save_and_load()
