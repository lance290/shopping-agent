"""Tests for choice factor filtering."""

import pytest
from sourcing.choice_filter import (
    matches_choice_constraint,
    should_exclude_by_choices,
    extract_choice_constraints,
)


class TestMatchesChoiceConstraint:
    """Test individual constraint matching."""

    def test_color_match(self):
        """Test that color constraint matches correctly."""
        assert matches_choice_constraint("Green T-Shirt", "color", "green")
        assert matches_choice_constraint("Dark green sweater", "color", "green")
        assert not matches_choice_constraint("Blue T-Shirt", "color", "green")

    def test_size_match(self):
        """Test that size constraint matches correctly."""
        assert matches_choice_constraint("T-Shirt Size XL", "size", "XL")
        assert matches_choice_constraint("Shirt - XL", "size", "xl")  # case insensitive
        assert not matches_choice_constraint("T-Shirt Size L", "size", "XL")

    def test_material_match(self):
        """Test that material constraint matches correctly."""
        assert matches_choice_constraint("Cotton T-Shirt", "material", "cotton")
        assert matches_choice_constraint("100% cotton fabric", "material", "cotton")
        assert not matches_choice_constraint("Polyester shirt", "material", "cotton")

    def test_short_value_word_boundary(self):
        """Test that short values use word boundary matching."""
        # "XL" should match "XL" but not "XXL"
        assert matches_choice_constraint("Shirt XL", "size", "XL")
        assert not matches_choice_constraint("Shirt XXL", "size", "XL")

    def test_boolean_true_match(self):
        """Test that boolean True values check for key in title."""
        assert matches_choice_constraint("Waterproof jacket", "waterproof", True)
        assert not matches_choice_constraint("Regular jacket", "waterproof", True)

    def test_boolean_false_skip(self):
        """Test that boolean False values are skipped."""
        assert matches_choice_constraint("Waterproof jacket", "waterproof", False)
        assert matches_choice_constraint("Regular jacket", "waterproof", False)

    def test_empty_values(self):
        """Test that empty values are skipped."""
        assert matches_choice_constraint("Any product", "color", "")
        assert matches_choice_constraint("Any product", "color", None)

    def test_special_values_skip(self):
        """Test that special values like 'not answered' are skipped."""
        assert matches_choice_constraint("Any product", "color", "not answered")
        assert matches_choice_constraint("Any product", "color", "No")

    def test_price_constraints_skip(self):
        """Test that price constraints are always skipped."""
        assert matches_choice_constraint("Expensive item", "min_price", 100)
        assert matches_choice_constraint("Cheap item", "max_price", 50)


class TestShouldExcludeByChoices:
    """Test overall exclusion logic."""

    def test_no_constraints(self):
        """Test that no constraints means no exclusion."""
        assert not should_exclude_by_choices("Green T-Shirt", None)
        assert not should_exclude_by_choices("Green T-Shirt", {})

    def test_matching_single_constraint(self):
        """Test that matching single constraint is not excluded."""
        choices = {"color": "green"}
        assert not should_exclude_by_choices("Green T-Shirt", choices)

    def test_non_matching_single_constraint(self):
        """Test that non-matching single constraint is excluded."""
        choices = {"color": "green"}
        assert should_exclude_by_choices("Blue T-Shirt", choices)

    def test_matching_multiple_constraints(self):
        """Test that all matching constraints is not excluded."""
        choices = {"color": "green", "size": "XL"}
        assert not should_exclude_by_choices("Green T-Shirt XL", choices)

    def test_partial_matching_constraints(self):
        """Test that partial matching is excluded."""
        choices = {"color": "green", "size": "XL"}
        # Has green but not XL
        assert should_exclude_by_choices("Green T-Shirt L", choices)

    def test_price_constraints_ignored(self):
        """Test that price constraints don't cause exclusion."""
        choices = {"color": "green", "min_price": 10, "max_price": 100}
        assert not should_exclude_by_choices("Green T-Shirt", choices)
        assert should_exclude_by_choices("Blue T-Shirt", choices)

    def test_notes_fields_ignored(self):
        """Test that meta fields like notes are ignored."""
        choices = {"color": "green", "notes": "some random text"}
        assert not should_exclude_by_choices("Green T-Shirt", choices)
        # Should not exclude based on notes
        assert not should_exclude_by_choices("Blue T-Shirt without notes text", {"notes": "some text"})

    def test_case_insensitive_matching(self):
        """Test that matching is case insensitive."""
        choices = {"color": "GREEN"}
        assert not should_exclude_by_choices("green t-shirt", choices)
        assert not should_exclude_by_choices("Green T-Shirt", choices)
        assert not should_exclude_by_choices("GREEN SHIRT", choices)


class TestExtractChoiceConstraints:
    """Test extraction of choice constraints from JSON."""

    def test_empty_input(self):
        """Test that empty input returns empty dict."""
        assert extract_choice_constraints(None) == {}
        assert extract_choice_constraints("") == {}

    def test_valid_json(self):
        """Test that valid JSON is parsed correctly."""
        json_str = '{"color": "green", "size": "XL"}'
        result = extract_choice_constraints(json_str)
        assert result == {"color": "green", "size": "XL"}

    def test_filter_price_constraints(self):
        """Test that price constraints are filtered out."""
        json_str = '{"color": "green", "min_price": 10, "max_price": 100}'
        result = extract_choice_constraints(json_str)
        assert result == {"color": "green"}
        assert "min_price" not in result
        assert "max_price" not in result

    def test_filter_meta_fields(self):
        """Test that meta fields are filtered out."""
        json_str = '{"color": "green", "notes": "some notes", "comments": "test"}'
        result = extract_choice_constraints(json_str)
        assert result == {"color": "green"}

    def test_filter_empty_values(self):
        """Test that empty values are filtered out."""
        json_str = '{"color": "green", "size": "", "material": "not answered"}'
        result = extract_choice_constraints(json_str)
        assert result == {"color": "green"}

    def test_invalid_json(self):
        """Test that invalid JSON returns empty dict."""
        result = extract_choice_constraints("invalid json")
        assert result == {}

    def test_complex_values(self):
        """Test that various value types are preserved."""
        json_str = '{"color": "green", "waterproof": true, "size": "XL", "quantity": 5}'
        result = extract_choice_constraints(json_str)
        assert result == {"color": "green", "waterproof": True, "size": "XL", "quantity": 5}
