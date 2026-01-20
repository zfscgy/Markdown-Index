from markdown_index.utils import get_table_ranges, fuzzy_score


def test__get_tables():
    markdown = open("tests/data/中华人民共和国国内生产总值.md", "r", encoding="utf-8").read()
    md_lines = markdown.split("\n")
    tables = get_table_ranges(markdown)
    for start, end in tables:
        print("========= Table ==========")
        print("\n".join(md_lines[start:end]))


def test__fuzzy_search():
    text = "……交通事故肇事逃逸……"
    pattern = "交通肇事"
    score = fuzzy_score(text, pattern)
    print(score)

if __name__ == "__main__":
    test__fuzzy_search()