from markdown_index.utils import get_table_ranges


def test__get_tables():
    markdown = open("tests/中华人民共和国国内生产总值.md", "r", encoding="utf-8").read()
    md_lines = markdown.split("\n")
    tables = get_table_ranges(markdown)
    for start, end in tables:
        print("========= Table ==========")
        print("\n".join(md_lines[start:end]))
        


if __name__ == "__main__":
    test__get_tables()
