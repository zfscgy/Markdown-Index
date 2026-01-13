from typing import Tuple, List

from importlib import resources

import re
import json

from tokenizers import Tokenizer


def get_tokenizer(model_name: str) -> Tokenizer:    
    tokenizers_dir = resources.files("markdown_index") / "tokenizer_files"
    name_to_file = {
        "qwen": tokenizers_dir / "tokenizer__qwen.json",
        "deepseek": tokenizers_dir / "tokenizer__deepseek.json",
        "gpt": tokenizers_dir / "tokenizer__gpt-oss.json",
        "gemini": tokenizers_dir / "tokenizer__gemma.json",
        "default": tokenizers_dir / "tokenizer__qwen.json",
    }
    file_name = name_to_file.get(model_name, name_to_file["default"])
    return Tokenizer.from_file(file_name.as_posix())


def get_table_ranges(markdown_content: str) -> List[Tuple[int, int]]:
    lines = markdown_content.split('\n')
    
    table_ranges = []

    in_table: str = "no"  # header-0 | header-1 | body | no
    
    current_table_start = None
    current_table_cols = None
    for i in range(len(lines)):
        line = lines[i].strip()
        if (len(line) >= 2) and (line[0] == line[-1] == "|"):
            if in_table == "no":
                in_table = "header-0"
                current_table_start = i
                current_table_cols = line.count("|")
            elif in_table == "header-0":
                # This line is made of "|" and "-", so we believe it is the table header line
                if (line.count("|") == current_table_cols) and \
                    ("---" in line) and \
                    (re.fullmatch(r"[|\-\s]+", line) is not None):
                    in_table = "header-1"
                else:
                    current_table_start = None
                    in_table = "no"  # Unexpected second row, exit
            elif in_table in ["header-1", "body"]:
                in_table = "body"
            else:  # Shall not be executed
                pass
        else:
            if in_table in ["header-0", "header-1", "body"]:
                table_ranges.append((current_table_start, i))
            in_table = "no"

    return table_ranges


def extract_json_object(llm_response: str) -> dict:
    # Try to extract JSON directly
    try:
        return json.loads(llm_response)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON in Markdown foramt
    try:
        lines = llm_response.split("\n")
        json_start_line = lines.index("```json")
        json_end_line = lines.index("```")
        json_content = "\n".join(lines[json_start_line + 1:json_end_line])
        return json.loads(json_content)
    except (IndexError, json.JSONDecodeError):
        pass

    # Try to mannually find JSON content enclosed by { ... } (support nested)
    try:
        json_level = 0
        json_start = None
        json_end = None
        for i, char in enumerate(llm_response):
            if char == "{":
                json_level += 1
                if json_level == 1:
                    json_start = i

            elif char == "}":
                json_level -= 1
                if json_level == 0:
                    json_end = i
                    break
        json_content = llm_response[json_start:json_end + 1]
        return json.loads(json_content)
    except (json.JSONDecodeError):
        pass

    raise ValueError(f"Failed to extract JSON object from LLM response: {llm_response}")
