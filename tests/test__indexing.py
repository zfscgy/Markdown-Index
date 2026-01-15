import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from markdown_index.markdown_index import MarkdownIndex


def test__indexing():
    markdown_content = open("tests/data/中华人民共和国国内生产总值.md", "r", encoding="utf-8").read()
    index = MarkdownIndex(markdown_content, openai_model_name="google/gemini-3-flash-preview", language="cn")
    print(index.serialize_index())

    markdown_content = open("tests/data/中华人民共和国刑法.md", "r", encoding="utf-8").read()
    index = MarkdownIndex(markdown_content, openai_model_name="google/gemini-3-flash-preview", language="cn")
    print(index.serialize_index())

    markdown_content = open("tests/data/Survey-of-Chatbots.md", "r", encoding="utf-8").read()
    index = MarkdownIndex(markdown_content, openai_model_name="google/gemini-3-flash-preview", language="en")
    print(index.serialize_index())


if __name__ == "__main__":
    test__indexing()
