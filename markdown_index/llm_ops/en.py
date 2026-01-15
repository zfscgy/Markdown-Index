from typing import Callable

from textwrap import dedent

from markdown_index.llm_ops.base import Templates


en_templates = Templates(
    text_summary_prompt_template = lambda content, n_words: dedent(f"""\
        You need to generate a description based on the document content, summarizing the main points and key information.
        Note: Keep the description as concise as possible. Remove unnecessary or repetitive wording, extract only the key content, and keep it within {n_words} words whenever possible.
        [Output requirements]:
        Return the result in the following JSON format:
        {{
            "summary": "(document summary)"
        }}
        Do not return any other text, wording, or formatting symbols.
        
        Below is the document content:
        ---------------
        ```text
        """) + content + dedent(f"""
        ```
        """),

    text_keywords_prompt_template = lambda query: dedent(f"""\
        You need to extract keywords based on the user's query. The keywords should accurately capture the user's intent and be usable for retrieval.
        Note: The keyword list should be as comprehensive as possible, and individual keywords should not be too long. When it does not affect the semantics or when semantics are close, choose the main part of the word to avoid retrieval failures.
        For example: "neural network theory" can extract "neural network", "DNN", "deep learning", etc., because the complete "neural network theory" may not match the target content.
        In addition, to prevent some synonyms from not being properly retrieved, you need to consider whether keywords have synonyms/very close near-synonyms, and if so, you need to return the synonyms/near-synonyms as well.
        Note that except for some names or proper nouns, synonyms do not need to include translations of that keyword in other languages.
        [Output requirements]: Please return in the JSON format shown in the example. Do not return any other text, wording, or formatting symbols.
        [Example]:
        - User query: What is the relationship between Einstein's theory of relativity and quantum mechanics?
        - Your output:
        ```json
        [
            {{
                "keyword": "Einstein",
                "synonyms": ["Albert Einstein"]
            }},
            {{
                "keyword": "relativity",
                "synonyms": ["theory of relativity", "relativity theory"]
            }},
            {{
                "keyword": "quantum mechanics",
                "synonyms": ["quantum", "quantum physics", "quantum theory"]
            }} 
        ]
        ```

        Below is the user's query:
        ------------------
        ```text
        """) + query + dedent("""
        ```
        """),

    # Not implemented yet in `LLMOps` (placeholders for `Templates` completeness).
    retrieve_index_prompt_template = lambda query, index: dedent(f"""\
        You are a document retrieval expert. You need to find the document segments most relevant to the user's query from the given document index.
        We have split the document into non-overlapping segments and then built a document index, which contains the segment ID, title, and summary of each document segment.
        Note: The index may not be complete (because the complete index might be too long), you only need to consider the index currently sent to you.
        [Output requirements]:
        Return the result in the following JSON format:
        {{
            "related_block_ids": [(list of document segment IDs)]
        }}
        Do not return any other text, wording, or formatting symbols. Put the most important IDs first. If you think there are no relevant ones, the list can be empty.

        Below is the document index:
        ------------------
        ```json        
        """) + index + dedent("""\
        ```

        Below is the user's query:
        ------------------
        ```text
        """) + query + dedent("""
        ```
        """),

    retrieve_block_prompt_template = lambda query, block_list: dedent(f"""\
        You are a document retrieval expert. You need to find the statements most relevant to the user's query from the given list of document segments.
        Because document segments are generally long, you need to extract the statements most relevant to the user's query from the long document segments and return them.
        
        Note that the content you extract should be as complete as possible and should not omit important information relevant to the user's query.
        Pay special attention to Markdown tables. If a row in a table is relevant to the user's content, you should not only extract that row, but also extract the table **header**, otherwise the content will be incomplete and incomprehensible.
        You can extract multiple relevant statements, but if you do not find content truly relevant to the user's query, please return an empty list directly.
        
        [Output requirements]:
        Return the result in the following JSON format:
        [
            {{
                "block_id": "(document segment ID)",
                "related_text": "(statement most relevant to the user's query)"
            }},
            ...
        ]
        Do not return any other text, wording, or formatting symbols.

       Below is the user's query:
        ------------------
        ```text
        """) + query + dedent("""
        ```

        Below is the list of document segments:
        ------------------
        ```json
        """) + block_list + dedent("""
        ```
        """)
)
