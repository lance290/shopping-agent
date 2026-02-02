"""Tests for material filtering utilities."""

import pytest
from sourcing.material_filter import (
    contains_synthetic_material,
    extract_material_constraints,
    should_exclude_result,
)


class TestContainsSyntheticMaterial:
    """Tests for contains_synthetic_material function."""

    def test_detects_faux_leather(self):
        """Should detect faux leather in product titles."""
        assert contains_synthetic_material("Modern Faux Leather Office Chair")
        assert contains_synthetic_material("Ergonomic chair with faux-leather upholstery")
        assert contains_synthetic_material("VEGAN LEATHER swivel chair")

    def test_detects_pu_material(self):
        """Should detect PU (polyurethane) in product titles."""
        assert contains_synthetic_material("Executive PU Leather Chair")
        assert contains_synthetic_material("Office chair with PU upholstery")
        assert contains_synthetic_material("Polyurethane office chair")

    def test_detects_synthetic_terms(self):
        """Should detect various synthetic material terms."""
        assert contains_synthetic_material("Plastic office chair")
        assert contains_synthetic_material("Vinyl upholstered chair")
        assert contains_synthetic_material("Polyester fabric chair")
        assert contains_synthetic_material("Nylon mesh back chair")

    def test_detects_composite_materials(self):
        """Should detect composite and bonded materials."""
        assert contains_synthetic_material("Bonded leather executive chair")
        assert contains_synthetic_material("Laminated wood desk chair")
        assert contains_synthetic_material("Particle board base chair")

    def test_allows_natural_materials(self):
        """Should not flag natural materials."""
        assert not contains_synthetic_material("Solid wood office chair")
        assert not contains_synthetic_material("Genuine leather executive chair")
        assert not contains_synthetic_material("100% cotton upholstered chair")
        assert not contains_synthetic_material("Oak and steel swivel chair")
        assert not contains_synthetic_material("Natural fiber chair")
        assert not contains_synthetic_material("Hemp and bamboo chair")

    def test_handles_empty_input(self):
        """Should handle None and empty strings."""
        assert not contains_synthetic_material(None)
        assert not contains_synthetic_material("")
        assert not contains_synthetic_material("   ")

    def test_case_insensitive(self):
        """Should be case-insensitive."""
        assert contains_synthetic_material("FAUX LEATHER CHAIR")
        assert contains_synthetic_material("faux leather chair")
        assert contains_synthetic_material("Faux Leather Chair")

    def test_word_boundary_for_abbreviations(self):
        """Should use word boundaries for short abbreviations like PU."""
        # Should match
        assert contains_synthetic_material("PU leather chair")
        assert contains_synthetic_material("Chair with PU upholstery")

        # Should NOT match (PU not as standalone word)
        assert not contains_synthetic_material("PURPLE chair")
        assert not contains_synthetic_material("PUSH-back office chair")


class TestExtractMaterialConstraints:
    """Tests for extract_material_constraints function."""

    def test_detects_no_plastic_constraint(self):
        """Should detect 'no plastic' constraints."""
        constraints = {"material": "no plastic"}
        exclude_synthetics, custom_keywords = extract_material_constraints(constraints)
        assert exclude_synthetics is True

    def test_detects_no_petroleum_constraint(self):
        """Should detect 'no petroleum' constraints."""
        constraints = {"material": "no petroleum"}
        exclude_synthetics, custom_keywords = extract_material_constraints(constraints)
        assert exclude_synthetics is True

    def test_detects_without_synthetic_constraint(self):
        """Should detect 'without synthetic' constraints."""
        constraints = {"material": "without synthetic materials"}
        exclude_synthetics, custom_keywords = extract_material_constraints(constraints)
        assert exclude_synthetics is True

    def test_detects_exclude_plastic_constraint(self):
        """Should detect 'exclude plastic' constraints."""
        constraints = {"plastic": "exclude"}
        exclude_synthetics, custom_keywords = extract_material_constraints(constraints)
        assert exclude_synthetics is True

    def test_extracts_no_prefix_constraints(self):
        """Should extract materials from 'no X' constraint keys."""
        constraints = {"no vinyl": "true", "no nylon": "yes"}
        exclude_synthetics, custom_keywords = extract_material_constraints(constraints)
        assert "vinyl" in custom_keywords
        assert "nylon" in custom_keywords

    def test_extracts_without_constraints(self):
        """Should extract materials from 'without X' values."""
        constraints = {"material": "without vinyl and nylon"}
        exclude_synthetics, custom_keywords = extract_material_constraints(constraints)
        # The function extracts text after "without"
        assert len(custom_keywords) > 0

    def test_handles_empty_constraints(self):
        """Should handle empty constraints."""
        exclude_synthetics, custom_keywords = extract_material_constraints({})
        assert exclude_synthetics is False
        assert len(custom_keywords) == 0

    def test_handles_none_values(self):
        """Should handle None values in constraints."""
        constraints = {"material": None, "color": "blue"}
        exclude_synthetics, custom_keywords = extract_material_constraints(constraints)
        # Should not crash

    def test_case_insensitive_matching(self):
        """Should handle different cases."""
        constraints = {"Material": "No Plastic", "NO_PETROLEUM": "exclude"}
        exclude_synthetics, custom_keywords = extract_material_constraints(constraints)
        assert exclude_synthetics is True


class TestShouldExcludeResult:
    """Tests for should_exclude_result function."""

    def test_excludes_synthetic_materials_when_requested(self):
        """Should exclude products with synthetic materials."""
        assert should_exclude_result("Faux Leather Office Chair", exclude_synthetics=True)
        assert should_exclude_result("PU Upholstered Chair", exclude_synthetics=True)
        assert should_exclude_result("Vinyl Executive Chair", exclude_synthetics=True)

    def test_allows_natural_materials_when_synthetics_excluded(self):
        """Should allow natural materials even when excluding synthetics."""
        assert not should_exclude_result("Solid Oak Wood Chair", exclude_synthetics=True)
        assert not should_exclude_result("Genuine Leather Chair", exclude_synthetics=True)
        assert not should_exclude_result("100% Cotton Chair", exclude_synthetics=True)

    def test_excludes_custom_keywords(self):
        """Should exclude products with custom keywords."""
        custom_keywords = {"velvet", "suede"}
        assert should_exclude_result("Velvet Office Chair", custom_exclude_keywords=custom_keywords)
        assert should_exclude_result("Suede Upholstered Chair", custom_exclude_keywords=custom_keywords)

    def test_allows_without_custom_keywords(self):
        """Should allow products without custom keywords."""
        custom_keywords = {"velvet", "suede"}
        assert not should_exclude_result("Leather Office Chair", custom_exclude_keywords=custom_keywords)

    def test_handles_empty_title(self):
        """Should handle None and empty titles."""
        assert not should_exclude_result(None, exclude_synthetics=True)
        assert not should_exclude_result("", exclude_synthetics=True)

    def test_allows_all_when_no_constraints(self):
        """Should allow all products when no constraints are set."""
        assert not should_exclude_result("Faux Leather Chair")
        assert not should_exclude_result("PU Office Chair")
        assert not should_exclude_result("Any Chair")

    def test_combined_constraints(self):
        """Should handle both synthetic exclusion and custom keywords."""
        custom_keywords = {"metal"}
        # Excluded due to synthetics
        assert should_exclude_result(
            "Faux Leather Office Chair",
            exclude_synthetics=True,
            custom_exclude_keywords=custom_keywords
        )
        # Excluded due to custom keyword
        assert should_exclude_result(
            "Metal Frame Office Chair",
            exclude_synthetics=True,
            custom_exclude_keywords=custom_keywords
        )
        # Allowed (natural material, no custom keywords)
        assert not should_exclude_result(
            "Solid Wood Office Chair",
            exclude_synthetics=True,
            custom_exclude_keywords=custom_keywords
        )
