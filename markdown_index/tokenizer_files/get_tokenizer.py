from importlib import resources

from tokenizers import Tokenizer


tokenizers_dir = resources.files("tokenizers_dir")


name_to_file = {
    "qwen": tokenizers_dir / "tokenizer__qwen.json",
    "deepseek": tokenizers_dir / "tokenizer__deepseek.json",
    "gpt": tokenizers_dir / "tokenizer__gpt-oss.json",
    "gemini": tokenizers_dir / "tokenizer__gemma.json",
    "default": tokenizers_dir / "tokenizer__qwen.json",
}


def get_tokenizer(model_name: str) -> Tokenizer:
    file_name = name_to_file.get(model_name, name_to_file["default"])
    return Tokenizer.from_file(file_name)