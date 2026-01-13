from textwrap import dedent

from markdown_index.llm_ops.base import Templates


en_templates = Templates(
    text_summary_prompt_template = lambda content: dedent(f"""\
        Generate a short description based on the document content, summarizing the main points and key information.
        Note: Keep the description as concise as possible. Remove unnecessary or repetitive wording, extract only the key content, and keep it within 50 words whenever possible.
        [Output requirements]:
        Return the result in the following JSON format:
        {{
            "summary": "(document summary)"
        }}
        Do not return any other text, wording, or formatting symbols.
        
        Below is the document content:
        ---------------
        ```text
        """) + content + dedent(f"""\
        ```
        """),

    text_keywords_prompt_template = lambda query: dedent(f"""\
        Generate a keyword list based on the user's query. The keywords should accurately capture the user's intent and be usable for retrieval.
        Note: Make the keyword list as comprehensive as possible.
        [Output requirements]: Return a list of keywords separated by a single space. Do not return any other text, wording, or formatting symbols.
        [Example]:
         - User query: What is the relationship between Einstein's theory of relativity and quantum mechanics?
         - Your output: Einstein relativity quantum mechanics relationship

        Below is the user's query:
        ------------------
        ```text
        {query}
        ```
        """),

    # Not implemented yet in `LLMOps` (placeholders for `Templates` completeness).
    retrieve_index_prompt_template = lambda query: (_ for _ in ()).throw(NotImplementedError("retrieve_index_prompt_template is not implemented")),
    retrieve_block_prompt_template = lambda query: (_ for _ in ()).throw(NotImplementedError("retrieve_block_prompt_template is not implemented")),
    retrieve_content_prompt_template = lambda query: (_ for _ in ()).throw(NotImplementedError("retrieve_content_prompt_template is not implemented")),
)