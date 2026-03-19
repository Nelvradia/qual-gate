"""Unit tests for cli.resolve_profile."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.resolve_profile import (
    ProfileCircularError,
    ProfileDepthError,
    ProfileLoadError,
    ProfileToggleError,
    merge_profiles,
    resolve_profile,
    validate_toggles,
)

PROFILES_DIR = Path(__file__).parent.parent / "fixtures" / "profiles"


class TestNoExtends:
    """Profile without extends returns as-is."""

    def test_base_profile_unchanged(self) -> None:
        result = resolve_profile(PROFILES_DIR / "base.yaml")
        assert result["name"] == "base-project"
        assert result["stack"]["languages"] == ["python", "rust"]
        assert result["toggles"]["permission_system"] is True
        assert "extends" not in result


class TestSingleLevelInheritance:
    """Child extends base: scalars override, lists replace, objects deep-merge."""

    def test_scalar_override(self) -> None:
        result = resolve_profile(PROFILES_DIR / "child.yaml")
        assert result["name"] == "child-project", "Child name should override parent"

    def test_list_replace(self) -> None:
        result = resolve_profile(PROFILES_DIR / "child.yaml")
        assert result["stack"]["languages"] == ["python"], (
            "Child languages should replace parent's [python, rust]"
        )

    def test_object_deep_merge(self) -> None:
        result = resolve_profile(PROFILES_DIR / "child.yaml")
        # Child adds docs_dir, parent's source_dirs and test_dirs preserved
        assert result["paths"]["docs_dir"] == "docs/reference/"
        assert result["paths"]["source_dirs"] == ["src/"]
        assert result["paths"]["test_dirs"] == ["tests/"]

    def test_toggle_enable(self) -> None:
        result = resolve_profile(PROFILES_DIR / "child.yaml")
        assert result["toggles"]["permission_system"] is True, "Inherited toggle preserved"
        assert result["toggles"]["gdpr_scope"] is True, "Child enables new toggle"

    def test_parent_ci_platform_inherited(self) -> None:
        result = resolve_profile(PROFILES_DIR / "child.yaml")
        assert result["stack"]["ci_platform"] == "gitlab-ci", "Parent field inherited"


class TestMultiLevelInheritance:
    """Two-level and three-level chains work correctly."""

    def test_two_level_chain(self) -> None:
        result = resolve_profile(PROFILES_DIR / "child.yaml")
        # child → base (2 levels, depth 0 and 1)
        assert result["name"] == "child-project"
        assert result["toggles"]["permission_system"] is True

    def test_three_level_chain(self) -> None:
        result = resolve_profile(PROFILES_DIR / "grandchild.yaml")
        # grandchild → child → base (3 levels)
        assert result["name"] == "grandchild-project"
        assert result["version"] == "2.0.0"
        assert result["stack"]["languages"] == ["python"], "From child override"
        assert result["toggles"]["permission_system"] is True, "From base"
        assert result["toggles"]["gdpr_scope"] is True, "From child"
        assert result["paths"]["docs_dir"] == "docs/reference/", "From child"
        assert result["paths"]["source_dirs"] == ["src/"], "From base"


class TestDepthLimit:
    """Four-level chain exceeds max depth of 3."""

    def test_four_level_raises_depth_error(self) -> None:
        with pytest.raises(ProfileDepthError, match="exceeds max depth"):
            resolve_profile(PROFILES_DIR / "great-grandchild.yaml")


class TestCircularReference:
    """Circular extends chain detected and reported."""

    def test_circular_raises_error(self) -> None:
        with pytest.raises(ProfileCircularError, match="Circular reference"):
            resolve_profile(PROFILES_DIR / "circular-a.yaml")


class TestToggleSafety:
    """Child cannot disable parent toggles."""

    def test_toggle_violation_raises_error(self) -> None:
        with pytest.raises(ProfileToggleError, match="permission_system"):
            resolve_profile(PROFILES_DIR / "toggle-violation.yaml")


class TestMissingParent:
    """Missing parent profile gives a clear error."""

    def test_missing_parent_raises_load_error(self, tmp_path: Path) -> None:
        child = tmp_path / "child.yaml"
        child.write_text("extends: ./nonexistent.yaml\nname: orphan\n")
        with pytest.raises(ProfileLoadError, match="not found"):
            resolve_profile(child)


class TestMergeProfiles:
    """Direct tests for the merge function."""

    def test_scalar_override(self) -> None:
        parent = {"name": "parent", "version": "1.0"}
        child = {"name": "child"}
        result = merge_profiles(parent, child)
        assert result["name"] == "child"
        assert result["version"] == "1.0"

    def test_list_replace(self) -> None:
        parent = {"items": [1, 2, 3]}
        child = {"items": [4, 5]}
        result = merge_profiles(parent, child)
        assert result["items"] == [4, 5]

    def test_dict_deep_merge(self) -> None:
        parent = {"config": {"a": 1, "b": 2}}
        child = {"config": {"b": 3, "c": 4}}
        result = merge_profiles(parent, child)
        assert result["config"] == {"a": 1, "b": 3, "c": 4}

    def test_child_adds_new_key(self) -> None:
        parent = {"a": 1}
        child = {"b": 2}
        result = merge_profiles(parent, child)
        assert result == {"a": 1, "b": 2}

    def test_no_mutation(self) -> None:
        parent = {"config": {"a": [1, 2]}}
        child = {"config": {"a": [3]}}
        merge_profiles(parent, child)
        assert parent["config"]["a"] == [1, 2], "Parent should not be mutated"


class TestValidateToggles:
    """Direct tests for toggle validation."""

    def test_no_violations(self) -> None:
        parent = {"toggles": {"a": True, "b": False}}
        child = {"toggles": {"b": True, "c": True}}
        assert validate_toggles(parent, child) == []

    def test_disable_violation(self) -> None:
        parent = {"toggles": {"a": True}}
        child = {"toggles": {"a": False}}
        errors = validate_toggles(parent, child)
        assert len(errors) == 1
        assert "a" in errors[0]

    def test_no_toggles(self) -> None:
        assert validate_toggles({}, {}) == []
        assert validate_toggles({"toggles": {}}, {}) == []
