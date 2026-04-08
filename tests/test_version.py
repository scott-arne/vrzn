import pytest
from vrzn.version import Version, parse_version


class TestParseVersion:
    """Test PEP 440 version parsing and normalization."""

    def test_simple_release(self):
        v = parse_version("1.2.3")
        assert v == Version(1, 2, 3)

    def test_pre_release_alpha(self):
        v = parse_version("1.0.0a1")
        assert v.pre == ("a", 1)

    def test_pre_release_beta(self):
        v = parse_version("1.0.0b2")
        assert v.pre == ("b", 2)

    def test_pre_release_rc(self):
        v = parse_version("1.0.0rc1")
        assert v.pre == ("rc", 1)

    def test_pre_release_with_hyphen(self):
        v = parse_version("1.0.0-rc1")
        assert v.pre == ("rc", 1)

    def test_pre_release_with_dot(self):
        v = parse_version("1.0.0.rc1")
        assert v.pre == ("rc", 1)

    def test_alpha_label_normalization(self):
        v = parse_version("1.0.0alpha1")
        assert v.pre == ("a", 1)

    def test_beta_label_normalization(self):
        v = parse_version("1.0.0beta1")
        assert v.pre == ("b", 1)

    def test_preview_label_normalization(self):
        v = parse_version("1.0.0preview1")
        assert v.pre == ("rc", 1)

    def test_c_label_normalization(self):
        v = parse_version("1.0.0c1")
        assert v.pre == ("rc", 1)

    def test_post_release(self):
        v = parse_version("1.0.0.post1")
        assert v.post == 1

    def test_dev_release(self):
        v = parse_version("1.0.0.dev1")
        assert v.dev == 1

    def test_combined_pre_and_dev(self):
        v = parse_version("1.0.0rc1.dev2")
        assert v.pre == ("rc", 1)
        assert v.dev == 2

    def test_epoch(self):
        v = parse_version("1!2.0.0")
        assert v.epoch == 1
        assert v.major == 2

    def test_comma_separated_tuple(self):
        v = parse_version("1, 2, 3")
        assert v == Version(1, 2, 3)

    def test_case_insensitive(self):
        v = parse_version("1.0.0RC1")
        assert v.pre == ("rc", 1)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_version("not.a.version")

    def test_invalid_empty_raises(self):
        with pytest.raises(ValueError):
            parse_version("")

    def test_invalid_two_part_raises(self):
        with pytest.raises(ValueError):
            parse_version("1.2")


class TestVersionProperties:
    """Test Version computed properties."""

    def test_normalized_simple(self):
        assert Version(1, 2, 3).normalized == "1.2.3"

    def test_normalized_pre(self):
        assert Version(1, 0, 0, pre=("rc", 1)).normalized == "1.0.0rc1"

    def test_normalized_post(self):
        assert Version(1, 0, 0, post=1).normalized == "1.0.0.post1"

    def test_normalized_dev(self):
        assert Version(1, 0, 0, dev=1).normalized == "1.0.0.dev1"

    def test_normalized_epoch(self):
        assert Version(2, 0, 0, epoch=1).normalized == "1!2.0.0"

    def test_normalized_full_combined(self):
        assert Version(1, 0, 0, pre=("rc", 1), dev=2).normalized == "1.0.0rc1.dev2"

    def test_base(self):
        assert Version(1, 2, 3, pre=("a", 1), post=2).base == "1.2.3"

    def test_info_tuple(self):
        assert Version(1, 2, 3).info_tuple == "1, 2, 3"

    def test_is_release_true(self):
        assert Version(1, 0, 0).is_release is True

    def test_is_release_false_pre(self):
        assert Version(1, 0, 0, pre=("a", 1)).is_release is False

    def test_is_release_false_post(self):
        assert Version(1, 0, 0, post=1).is_release is False

    def test_is_release_false_dev(self):
        assert Version(1, 0, 0, dev=1).is_release is False

    def test_str_is_normalized(self):
        v = Version(1, 0, 0, pre=("rc", 1))
        assert str(v) == "1.0.0rc1"


class TestVersionComparison:
    """Test PEP 440 version ordering."""

    def test_simple_ordering(self):
        assert parse_version("1.0.0") < parse_version("1.0.1")
        assert parse_version("1.0.1") < parse_version("1.1.0")
        assert parse_version("1.1.0") < parse_version("2.0.0")

    def test_pre_release_ordering(self):
        assert parse_version("1.0.0a1") < parse_version("1.0.0b1")
        assert parse_version("1.0.0b1") < parse_version("1.0.0rc1")
        assert parse_version("1.0.0rc1") < parse_version("1.0.0")

    def test_pre_release_number_ordering(self):
        assert parse_version("1.0.0a1") < parse_version("1.0.0a2")
        assert parse_version("1.0.0rc1") < parse_version("1.0.0rc2")

    def test_post_release_ordering(self):
        assert parse_version("1.0.0") < parse_version("1.0.0.post1")
        assert parse_version("1.0.0.post1") < parse_version("1.0.0.post2")

    def test_dev_release_ordering(self):
        assert parse_version("1.0.0.dev1") < parse_version("1.0.0")
        assert parse_version("1.0.0.dev1") < parse_version("1.0.0.dev2")

    def test_epoch_ordering(self):
        assert parse_version("1.0.0") < parse_version("1!0.0.1")

    def test_equality(self):
        assert parse_version("1.0.0") == parse_version("1.0.0")
        assert parse_version("1.0.0rc1") == parse_version("1.0.0rc1")


class TestVersionBump:
    """Test version bump operations."""

    # --- major/minor/patch bumps ---

    def test_bump_major(self):
        v = Version(1, 2, 3)
        assert v.bump_major() == Version(2, 0, 0)

    def test_bump_minor(self):
        v = Version(1, 2, 3)
        assert v.bump_minor() == Version(1, 3, 0)

    def test_bump_patch(self):
        v = Version(1, 2, 3)
        assert v.bump_patch() == Version(1, 2, 4)

    def test_bump_patch_clears_pre(self):
        v = Version(1, 0, 1, pre=("rc", 1))
        assert v.bump_patch() == Version(1, 0, 2)

    def test_bump_minor_clears_pre(self):
        v = Version(1, 0, 1, pre=("rc", 1))
        assert v.bump_minor() == Version(1, 1, 0)

    def test_bump_major_clears_pre(self):
        v = Version(1, 0, 1, pre=("rc", 1))
        assert v.bump_major() == Version(2, 0, 0)

    def test_bump_patch_clears_post(self):
        v = Version(1, 0, 0, post=1)
        assert v.bump_patch() == Version(1, 0, 1)

    def test_bump_patch_clears_dev(self):
        v = Version(1, 0, 0, dev=1)
        assert v.bump_patch() == Version(1, 0, 1)

    def test_bump_preserves_epoch(self):
        v = Version(1, 0, 0, epoch=1)
        assert v.bump_patch() == Version(1, 0, 1, epoch=1)

    # --- bump with --pre ---

    def test_bump_patch_with_pre(self):
        v = Version(1, 0, 0)
        assert v.bump_patch(pre_label="rc") == Version(1, 0, 1, pre=("rc", 1))

    def test_bump_minor_with_pre(self):
        v = Version(1, 0, 0)
        assert v.bump_minor(pre_label="a") == Version(1, 1, 0, pre=("a", 1))

    def test_bump_major_with_pre(self):
        v = Version(1, 0, 0)
        assert v.bump_major(pre_label="b") == Version(2, 0, 0, pre=("b", 1))

    def test_bump_patch_with_pre_from_prerelease(self):
        v = Version(1, 0, 1, pre=("rc", 1))
        assert v.bump_patch(pre_label="rc") == Version(1, 0, 2, pre=("rc", 1))

    def test_bump_minor_with_pre_from_prerelease(self):
        v = Version(1, 0, 1, pre=("rc", 1))
        assert v.bump_minor(pre_label="a") == Version(1, 1, 0, pre=("a", 1))

    def test_bump_major_with_pre_from_prerelease(self):
        v = Version(1, 0, 1, pre=("rc", 1))
        assert v.bump_major(pre_label="b") == Version(2, 0, 0, pre=("b", 1))

    # --- bump pre ---

    def test_bump_pre_increments(self):
        v = Version(1, 0, 1, pre=("rc", 1))
        assert v.bump_pre() == Version(1, 0, 1, pre=("rc", 2))

    def test_bump_pre_no_active_raises(self):
        v = Version(1, 0, 0)
        with pytest.raises(ValueError, match="no active pre-release"):
            v.bump_pre()

    def test_bump_pre_promote_label(self):
        v = Version(1, 0, 1, pre=("b", 2))
        assert v.bump_pre(label="rc") == Version(1, 0, 1, pre=("rc", 1))

    def test_bump_pre_same_label_increments(self):
        v = Version(1, 0, 1, pre=("rc", 1))
        assert v.bump_pre(label="rc") == Version(1, 0, 1, pre=("rc", 2))

    def test_bump_pre_backward_raises(self):
        v = Version(1, 0, 1, pre=("rc", 1))
        with pytest.raises(ValueError, match="backward"):
            v.bump_pre(label="a")

    def test_bump_pre_promote_from_alpha_to_beta(self):
        v = Version(1, 0, 1, pre=("a", 3))
        assert v.bump_pre(label="b") == Version(1, 0, 1, pre=("b", 1))

    # --- bump release ---

    def test_bump_release(self):
        v = Version(1, 0, 1, pre=("rc", 1))
        assert v.bump_release() == Version(1, 0, 1)

    def test_bump_release_preserves_epoch(self):
        v = Version(1, 0, 1, pre=("rc", 1), epoch=2)
        assert v.bump_release() == Version(1, 0, 1, epoch=2)

    def test_bump_release_already_final_raises(self):
        v = Version(1, 0, 0)
        with pytest.raises(ValueError, match="already a final release"):
            v.bump_release()

    def test_bump_release_post_only_raises(self):
        v = Version(1, 0, 0, post=1)
        with pytest.raises(ValueError, match="already a final release"):
            v.bump_release()
