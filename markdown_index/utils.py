from typing import Tuple, List


def get_tables(markdown_content: str) -> List[Tuple[int, int]]:
    lines = markdown_content.split('\n')
    
    table_ranges = []

    in_table: str = "no"  # header-0 | header-1 | body | no
    
    current_table_start = None
    current_table_cols = None
    for i in range(len(lines)):
        line = lines[i].strip()
        if line[0] == line[-1] == "|":
            if in_table == "no":
                in_table = "header-0"
                current_table_start = i
                current_table_cols = line.count("|")
            elif in_table == "header-0":
                # This line is made of "|" and "-", so we believe it is the table header line
                if (line.count("|") == current_table_cols) and \
                    ("---" in line) and \
                    (line.replace("-", "").replace("|", "").strip() == ""):  
                    in_table = "header-1"
                else:
                    current_table_start = None
                    in_table = "no"  # Unexpected second row, exit
            elif in_table in ["header-1", "body"]:
                if line.count("|") == current_table_cols:
                    in_table = "body"
                else:
                    table_ranges.append((current_table_start, i+1))  # The end row is exclusive
                    current_table_start = None
                    in_table = "no"  # Unexpected row, exit
            else:  # Shall not be executed
                pass

    return table_ranges
