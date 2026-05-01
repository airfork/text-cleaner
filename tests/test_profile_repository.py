from text_cleaner.profiles import ProfileRepository


def test_repository_creates_default_profiles_when_file_missing(tmp_path):
    repository = ProfileRepository(tmp_path / "profiles.toml")

    profiles = repository.load_or_create()

    assert "nbsp_cleanup" in profiles
    assert (tmp_path / "profiles.toml").exists()


def test_repository_saves_clear_profile(tmp_path):
    repository = ProfileRepository(tmp_path / "profiles.toml")
    profiles = repository.load_or_create()

    cleared = repository.clear_profile(profiles, "nbsp_cleanup")

    assert cleared["nbsp_cleanup"].operations == ()
    assert cleared["nbsp_cleanup"].replacements == ()
