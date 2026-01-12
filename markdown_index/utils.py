from typing import Tuple, List
import re

from importlib import resources

from tokenizers import Tokenizer


tokenizers_dir = resources.files("markdown_index") / "tokenizer_files"


name_to_file = {
    "qwen": tokenizers_dir / "tokenizer__qwen.json",
    "deepseek": tokenizers_dir / "tokenizer__deepseek.json",
    "gpt": tokenizers_dir / "tokenizer__gpt-oss.json",
    "gemini": tokenizers_dir / "tokenizer__gemma.json",
    "default": tokenizers_dir / "tokenizer__qwen.json",
}


def get_tokenizer(model_name: str) -> Tokenizer:
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
