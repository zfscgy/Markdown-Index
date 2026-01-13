from typing import Callable

from textwrap import dedent

from markdown_index.llm_ops.base import Templates


cn_templates = Templates(
    text_summary_prompt_template = lambda content, n_words: dedent(f"""\
        你需要根据文档的内容生成一段描述，概括文档的主要内容和关键内容。
        注意：你的描述要尽可能精简，减少不必要的、重复的语句，只提取其中的关键内容，尽可能在{n_words}个字以内。
        【输出要求】：
        请按照如下的JSON格式返回：
        {{
            "summary": "（文档的描述）"
        }}
        不要返回任何其他文本、话语或格式符号。
        
        下面是文档的内容：
        ---------------
        ```text
        """) + content + dedent(f"""\
        ```
        """),

    text_keywords_prompt_template = lambda query: dedent(f"""\
        你需要根据用户的查询请求生成一个关键词列表，关键词应该准确归纳用户的查询意图，并且可以用于后续的检索中。
        注意：关键词列表应该尽可能全面。
        【输出要求】：请返回用单个空格分隔的关键词列表，不要返回任何其他文本、话语或格式符号。
        【示例】：
         - 用户查询请求：请问爱因斯坦的相对论和量子力学之间有什么关系？
         - 你的输出：爱因斯坦 相对论 量子力学 关系

        下面是用户的查询请求：
        ------------------
        ```text
        """) + query + dedent("""\
        ```
        """),

    # Not implemented yet in `LLMOps` (placeholders for `Templates` completeness).
    retrieve_index_prompt_template = lambda query, index: dedent(f"""\
        你是一名文件检索专家，你需要根据用户的查询请求，从给定的文档索引中，查出和用户的请求最为相关的文档片段。
        我们已经将文档切分成了互相不重合的片段，然后构建一个文档索引，索引中包含文档片段的ID、标题和摘要。
        注意：索引可能不是完整的（因为完整的索引可能太长了），你只需要考虑当前发送给你的索引即可。
        【输出要求】：
        请按照如下的JSON格式返回：
        {{
            "related_block_ids": [（文档片段的ID列表）]
        }}
        不要返回任何其他文本、话语或格式符号。请把重要的ID放在前面。如果你觉得没有相关的，列表可以为空。

        下面是文档索引：
        ------------------
        ```json        
        """) + index + dedent("""\
        ```

        下面是用户的查询请求：
        ------------------
        ```text
        """) + query + dedent("""\
        ```
        """),

    retrieve_block_prompt_template = None,
    retrieve_content_prompt_template = None,
)