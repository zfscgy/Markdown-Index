from pageindex.page_index_md import\
    extract_nodes_from_markdown, extract_node_text_content, \
    update_node_list_with_text_token_count, tree_thinning_for_index, build_tree_from_nodes, split_heavy_nodes

with open("PageIndex/tests/mds/test-report.md", 'r', encoding='utf-8') as f:
    markdown_content = f.read()

print(f"Extracting nodes from markdown...")
node_list, markdown_lines = extract_nodes_from_markdown(markdown_content)

print(f"Extracting text content from nodes...")
nodes_with_content = extract_node_text_content(node_list, markdown_lines)

nodes_with_content = update_node_list_with_text_token_count(nodes_with_content, model="gpt-4.1")
print(f"Thinning nodes...")
nodes_with_content = tree_thinning_for_index(nodes_with_content, 500, model="gpt-4.1")

print(f"Splitting heavy nodes...")
nodes_with_content = split_heavy_nodes(nodes_with_content, markdown_lines, 2000, model="gpt-4.1")


print("Original length", len(markdown_content.removeprefix("# Start of Document\n")))
print("New length", len("".join([node['text'] for node in nodes_with_content])))

print(f"Building tree from nodes...")
tree_structure = build_tree_from_nodes(nodes_with_content)

