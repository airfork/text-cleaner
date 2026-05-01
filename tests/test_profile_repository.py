from text_cleaner.profiles import Profile, ProfileRepository, ReplacementRule, load_profiles


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


def test_repository_clear_profile_persists_to_disk(tmp_path):
    path = tmp_path / "profiles.toml"
    repository = ProfileRepository(path)
    profiles = repository.load_or_create()

    repository.clear_profile(profiles, "nbsp_cleanup")

    loaded = load_profiles(path)
    assert loaded["nbsp_cleanup"].operations == ()
    assert loaded["nbsp_cleanup"].replacements == ()


def test_repository_delete_profile_persists_non_final_deletion(tmp_path):
    path = tmp_path / "profiles.toml"
    repository = ProfileRepository(path)
    profiles = repository.load_or_create()

    deleted = repository.delete_profile(profiles, "nbsp_cleanup")

    assert "nbsp_cleanup" not in deleted
    assert "nbsp_cleanup" not in load_profiles(path)


def test_repository_delete_profile_persists_final_deletion(tmp_path):
    path = tmp_path / "profiles.toml"
    repository = ProfileRepository(path)
    profiles = {
        "only_profile": Profile(
            "only_profile",
            "Only profile",
            "Only profile",
            ["trim"],
        )
    }
    repository.save(profiles)

    deleted = repository.delete_profile(profiles, "only_profile")

    assert deleted == {}
    assert load_profiles(path) == {}


def test_repository_load_or_create_replaces_empty_profile_file_with_defaults(tmp_path):
    path = tmp_path / "profiles.toml"
    repository = ProfileRepository(path)
    repository.save({})

    profiles = repository.load_or_create()

    assert "nbsp_cleanup" in profiles
    assert "nbsp_cleanup" in load_profiles(path)


def test_repository_clear_profile_persists_empty_replacements(tmp_path):
    path = tmp_path / "profiles.toml"
    repository = ProfileRepository(path)
    profiles = {
        "custom": Profile(
            "custom",
            "Custom",
            "Custom replacements",
            ["trim"],
            [ReplacementRule(find="old", replace="new")],
        )
    }
    repository.save(profiles)

    repository.clear_profile(profiles, "custom")

    loaded = load_profiles(path)
    assert loaded["custom"].operations == ()
    assert loaded["custom"].replacements == ()
