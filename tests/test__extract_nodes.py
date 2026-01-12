from markdown_index import extract_nodes


def test__extract_nodes():
    markdown_content = open("tests/中华人民共和国国内生产总值.md", "r", encoding="utf-8").read()
    nodes = extract_nodes(markdown_content)
    assert "".join(node.text for node in nodes) == markdown_content
    for node in nodes:
        print("-------------------")
        print(node.text)


def test__extract_nodes_with_max_tokens_per_node():
    markdown_content = open("tests/中华人民共和国国内生产总值.md", "r", encoding="utf-8").read()
    nodes = extract_nodes(markdown_content, max_tokens_per_node=1500)
    assert "".join(node.text for node in nodes) == markdown_content
    for node in nodes:
        print("-------------------")
        print(node.text)



if __name__ == "__main__":
    test__extract_nodes()
    test__extract_nodes_with_max_tokens_per_node()