"""Test schema validation in llm_ops/base.py (Pydantic models)."""
import pytest

from markdown_index.llm_ops.base import (
    TextSummarySchema,
    TextKeywordSchema,
    RetrieveIndexSchema,
    RetrieveBlockItemSchema,
)
from pydantic import TypeAdapter, ValidationError


class TestTextSummarySchema:
    """Test TextSummarySchema validation"""
    
    def test_valid_schema(self):
        """Test valid text summary payload"""
        valid_data = {"summary": "This is a valid summary"}
        TextSummarySchema.model_validate(valid_data)
    
    def test_missing_summary_field(self):
        """Test that missing 'summary' field raises error"""
        invalid_data = {"description": "Wrong field"}
        with pytest.raises(ValidationError):
            TextSummarySchema.model_validate(invalid_data)
    
    def test_extra_field(self):
        """Test that extra fields raise error"""
        invalid_data = {"summary": "Valid", "extra": "Not allowed"}
        with pytest.raises(ValidationError):
            TextSummarySchema.model_validate(invalid_data)
    
    def test_wrong_type(self):
        """Test that wrong type for summary raises error"""
        invalid_data = {"summary": 123}
        with pytest.raises(ValidationError):
            TextSummarySchema.model_validate(invalid_data)


class TestTextKeywordsSchema:
    """Test list[TextKeywordSchema] validation"""
    
    def test_valid_schema(self):
        """Test valid keywords payload"""
        valid_data = [
            {"keyword": "Einstein", "synonyms": ["Albert Einstein"]},
            {"keyword": "relativity", "synonyms": []},
        ]
        TypeAdapter(list[TextKeywordSchema]).validate_python(valid_data)
    
    def test_missing_field(self):
        """Test that missing required fields raise error"""
        invalid_data = [{"keyword": "test"}]  # missing synonyms
        with pytest.raises(ValidationError):
            TypeAdapter(list[TextKeywordSchema]).validate_python(invalid_data)
    
    def test_wrong_synonyms_type(self):
        """Test that wrong type for synonyms raises error"""
        invalid_data = [{"keyword": "test", "synonyms": "string"}]
        with pytest.raises(ValidationError):
            TypeAdapter(list[TextKeywordSchema]).validate_python(invalid_data)
    
    def test_extra_field(self):
        """Test that extra fields raise error"""
        invalid_data = [{"keyword": "test", "synonyms": [], "extra": "field"}]
        with pytest.raises(ValidationError):
            TypeAdapter(list[TextKeywordSchema]).validate_python(invalid_data)


class TestRetrieveIndexSchema:
    """Test RetrieveIndexSchema validation"""
    
    def test_valid_schema(self):
        """Test valid retrieve index payload"""
        valid_data = {"related_block_ids": [1, 2, 3, 4]}
        RetrieveIndexSchema.model_validate(valid_data)
    
    def test_empty_list(self):
        """Test that empty list is valid"""
        valid_data = {"related_block_ids": []}
        RetrieveIndexSchema.model_validate(valid_data)
    
    def test_missing_field(self):
        """Test that missing field raises error"""
        invalid_data = {"blocks": [1, 2, 3]}
        with pytest.raises(ValidationError):
            RetrieveIndexSchema.model_validate(invalid_data)
    
    def test_wrong_item_type(self):
        """Test that non-integer items raise error"""
        invalid_data = {"related_block_ids": [1, "2", 3]}
        with pytest.raises(ValidationError):
            RetrieveIndexSchema.model_validate(invalid_data)


class TestRetrieveBlockSchema:
    """Test list[RetrieveBlockItemSchema] validation"""
    
    def test_valid_schema(self):
        """Test valid retrieve block payload"""
        valid_data = [
            {"block_id": 1, "related_text": "Some text"},
            {"block_id": 2, "related_text": "More text"},
        ]
        TypeAdapter(list[RetrieveBlockItemSchema]).validate_python(valid_data)
    
    def test_empty_list(self):
        """Test that empty list is valid"""
        valid_data = []
        TypeAdapter(list[RetrieveBlockItemSchema]).validate_python(valid_data)
    
    def test_missing_field(self):
        """Test that missing fields raise error"""
        invalid_data = [{"block_id": 1}]  # missing related_text
        with pytest.raises(ValidationError):
            TypeAdapter(list[RetrieveBlockItemSchema]).validate_python(invalid_data)
    
    def test_wrong_type(self):
        """Test that wrong types raise error"""
        invalid_data = [{"block_id": 123, "related_text": "text"}]
        with pytest.raises(ValidationError):
            TypeAdapter(list[RetrieveBlockItemSchema]).validate_python(invalid_data)
    
    def test_extra_field(self):
        """Test that extra fields raise error"""
        invalid_data = [
            {"block_id": 1, "related_text": "text", "extra": "field"}
        ]
        with pytest.raises(ValidationError):
            TypeAdapter(list[RetrieveBlockItemSchema]).validate_python(invalid_data)
