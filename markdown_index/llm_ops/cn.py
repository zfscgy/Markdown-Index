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
        你需要根据用户的查询请求提取关键词，关键词应该准确归纳用户的查询意图，并且可以用于后续的检索中。
        注意：关键词列表应该尽可能全面。
        此外，为了防止某些同义词无法被正确检索，你需要考虑关键词是否存在一些同义词，若有的话需要将同义词也返回。
        注意，除了一些姓名或专有名词，同义词无需包含该关键词在其他语言中的翻译。
        【输出要求】：请按照示例中的JSON格式返回，不要返回任何其他文本、话语或格式符号。
        【示例】：
        - 用户查询请求：请问爱因斯坦的相对论和量子力学之间有什么关系？
        - 你的输出：
        ```json
        [
            {{
                "keyword": "爱因斯坦",
                "synonyms": ["Einstein"]
            }},
            {{
                "keyword": "相对论",
                "synonyms": []
            }},
            {{
                "keyword": "量子力学",
                "synonyms": ["量子物理", "量子理论"]
            }} 
        ]
        ```

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

    retrieve_block_prompt_template = lambda query, block_list: dedent(f"""\
        你是一名文件检索专家，你需要根据用户的查询请求，从给定的文档片段的列表中，查出和用户的请求最为相关的语句。
        因为文档片段一般都比较长，所以你需要从长的文档片段中提取出和用户的请求最为相关的语句，然后返回。
        
        注意，你抽取的内容要尽量完整，不要遗漏和用户请求相关的重要信息。
        特别关注Markdown表格的情况，如果表格的某一行和用户内容相关，你不仅要抽取该行，你也要把表格的**标题**也进行抽取，否则会导致内容不完整、无法理解。
        你可以抽取多个相关的语句，但是如果你没有发现真正与用户的查询相关的内容，请直接返回一个空列表。
        
        【输出要求】：
        请按照如下的JSON格式返回：
        [
            {{
                "block_id": "(文档片段的ID)",
                "related_text": "(和用户的请求最为相关的语句)"
            }},
            ...
        ]
        不要返回任何其他文本、话语或格式符号。

       下面是用户的查询请求：
        ------------------
        ```text
        """) + query + dedent("""\
        ```

        下面是文档片段的列表：
        ------------------
        ```json
        """) + block_list + dedent("""\
        ```
        """),

    retrieve_content_prompt_template = None,
)