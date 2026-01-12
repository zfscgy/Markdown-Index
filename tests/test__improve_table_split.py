from markdown_index import extract_nodes
from markdown_index.markdown_index import improve_table_split


def test__improve_table_split():
    markdown_content = open("tests/中华人民共和国国内生产总值.md", "r", encoding="utf-8").read()
    nodes = extract_nodes(markdown_content, max_tokens_per_node=500)
    nodes = improve_table_split(markdown_content, nodes)
    for node in nodes:
        print("-------------------")
        print(node.text)


if __name__ == "__main__":
    test__improve_table_split()
