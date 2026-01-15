"""Test JSON schema validation in llm_ops/base.py"""
import pytest
from jsonschema import ValidationError
from jsonschema import validate

from markdown_index.llm_ops.base import (
    TEXT_SUMMARY_SCHEMA,
    TEXT_KEYWORDS_SCHEMA,
    RETRIEVE_INDEX_SCHEMA,
    RETRIEVE_BLOCK_SCHEMA,
)


class TestTextSummarySchema:
    """Test TEXT_SUMMARY_SCHEMA validation"""
    
    def test_valid_schema(self):
        """Test valid text summary JSON"""
        valid_data = {"summary": "This is a valid summary"}
        validate(instance=valid_data, schema=TEXT_SUMMARY_SCHEMA)
    
    def test_missing_summary_field(self):
        """Test that missing 'summary' field raises error"""
        invalid_data = {"description": "Wrong field"}
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=TEXT_SUMMARY_SCHEMA)
    
    def test_extra_field(self):
        """Test that extra fields raise error"""
        invalid_data = {"summary": "Valid", "extra": "Not allowed"}
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=TEXT_SUMMARY_SCHEMA)
    
    def test_wrong_type(self):
        """Test that wrong type for summary raises error"""
        invalid_data = {"summary": 123}
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=TEXT_SUMMARY_SCHEMA)


class TestTextKeywordsSchema:
    """Test TEXT_KEYWORDS_SCHEMA validation"""
    
    def test_valid_schema(self):
        """Test valid keywords JSON"""
        valid_data = [
            {"keyword": "Einstein", "synonyms": ["Albert Einstein"]},
            {"keyword": "relativity", "synonyms": []},
        ]
        validate(instance=valid_data, schema=TEXT_KEYWORDS_SCHEMA)
    
    def test_missing_field(self):
        """Test that missing required fields raise error"""
        invalid_data = [{"keyword": "test"}]  # missing synonyms
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=TEXT_KEYWORDS_SCHEMA)
    
    def test_wrong_synonyms_type(self):
        """Test that wrong type for synonyms raises error"""
        invalid_data = [{"keyword": "test", "synonyms": "string"}]
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=TEXT_KEYWORDS_SCHEMA)
    
    def test_extra_field(self):
        """Test that extra fields raise error"""
        invalid_data = [{"keyword": "test", "synonyms": [], "extra": "field"}]
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=TEXT_KEYWORDS_SCHEMA)


class TestRetrieveIndexSchema:
    """Test RETRIEVE_INDEX_SCHEMA validation"""
    
    def test_valid_schema(self):
        """Test valid retrieve index JSON"""
        valid_data = {"related_block_ids": [1, 2, 3, 4]}
        validate(instance=valid_data, schema=RETRIEVE_INDEX_SCHEMA)
    
    def test_empty_list(self):
        """Test that empty list is valid"""
        valid_data = {"related_block_ids": []}
        validate(instance=valid_data, schema=RETRIEVE_INDEX_SCHEMA)
    
    def test_missing_field(self):
        """Test that missing field raises error"""
        invalid_data = {"blocks": [1, 2, 3]}
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=RETRIEVE_INDEX_SCHEMA)
    
    def test_wrong_item_type(self):
        """Test that non-integer items raise error"""
        invalid_data = {"related_block_ids": [1, "2", 3]}
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=RETRIEVE_INDEX_SCHEMA)


class TestRetrieveBlockSchema:
    """Test RETRIEVE_BLOCK_SCHEMA validation"""
    
    def test_valid_schema(self):
        """Test valid retrieve block JSON"""
        valid_data = [
            {"block_id": "block1", "related_text": "Some text"},
            {"block_id": "block2", "related_text": "More text"},
        ]
        validate(instance=valid_data, schema=RETRIEVE_BLOCK_SCHEMA)
    
    def test_empty_list(self):
        """Test that empty list is valid"""
        valid_data = []
        validate(instance=valid_data, schema=RETRIEVE_BLOCK_SCHEMA)
    
    def test_missing_field(self):
        """Test that missing fields raise error"""
        invalid_data = [{"block_id": "block1"}]  # missing related_text
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=RETRIEVE_BLOCK_SCHEMA)
    
    def test_wrong_type(self):
        """Test that wrong types raise error"""
        invalid_data = [{"block_id": 123, "related_text": "text"}]
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=RETRIEVE_BLOCK_SCHEMA)
    
    def test_extra_field(self):
        """Test that extra fields raise error"""
        invalid_data = [
            {"block_id": "block1", "related_text": "text", "extra": "field"}
        ]
        with pytest.raises(ValidationError):
            validate(instance=invalid_data, schema=RETRIEVE_BLOCK_SCHEMA)
