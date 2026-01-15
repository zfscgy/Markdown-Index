from textwrap import dedent

from markdown_index.llm_ops.base import LLMOps, get_templates
from markdown_index.chat import LLMChat


chat = LLMChat(model="qwen/qwen3-next-80b-a3b-thinking")
llm_ops = LLMOps(chat=chat, templates=get_templates("cn"))

def test__text_keywords():
    print("Test text_keywords")
    queries = [
        "贪污受贿最多会判几年？",
        "如何从零开始学习使用Unity游戏引擎开发自己的FPS游戏？",
        "How to fine-tune an LLM model using the huggingface libraries? Provide me with some examples."
    ]
    
    for q in queries:
        result = llm_ops.text_keywords(q)
        print(result)
        print("------------------")


def test__text_summary():
    print("Test text_summary")
    content = open("tests/data/news1.txt", "r", encoding="utf-8").read()
    result = llm_ops.text_summary(content, 50)
    print(result)
    print("------------------")



if __name__ == "__main__":
    test__text_summary()
