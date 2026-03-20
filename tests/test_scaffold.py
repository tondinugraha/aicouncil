"""Tests for scaffold.py — auto-scaffold ./aicouncil/ directory."""

from aicouncil.scaffold import ensure_scaffold


class TestEnsureScaffold:
    """Test auto-scaffold directory creation."""

    def test_creates_directory_structure(self, tmp_path):
        result = ensure_scaffold(project_root=tmp_path)

        assert result == tmp_path / "aicouncil"
        assert result.is_dir()
        assert (result / "history").is_dir()
        assert (result / "agents").is_dir()

    def test_copies_default_config(self, tmp_path):
        ensure_scaffold(project_root=tmp_path)

        config_file = tmp_path / "aicouncil" / "config.yaml"
        assert config_file.exists()

        content = config_file.read_text()
        assert "default_model" in content
        assert "model_pool" in content
        assert "capability_weights" in content
        assert "tool_overrides" in content

    def test_idempotent_second_run(self, tmp_path):
        """Second run changes nothing."""
        ensure_scaffold(project_root=tmp_path)

        # Write a marker file
        marker = tmp_path / "aicouncil" / "marker.txt"
        marker.write_text("test")

        # Run again
        ensure_scaffold(project_root=tmp_path)

        # Marker still exists — directory was not recreated
        assert marker.exists()
        assert marker.read_text() == "test"

    def test_does_not_overwrite_existing_config(self, tmp_path):
        """If aicouncil/ already exists, config.yaml is preserved."""
        aicouncil_dir = tmp_path / "aicouncil"
        aicouncil_dir.mkdir()
        config_file = aicouncil_dir / "config.yaml"
        config_file.write_text("custom: true")

        ensure_scaffold(project_root=tmp_path)

        # Original content preserved
        assert config_file.read_text() == "custom: true"

    def test_creates_empty_history_dir(self, tmp_path):
        ensure_scaffold(project_root=tmp_path)
        history_dir = tmp_path / "aicouncil" / "history"
        assert history_dir.is_dir()
        assert list(history_dir.iterdir()) == []

    def test_creates_empty_agents_dir(self, tmp_path):
        ensure_scaffold(project_root=tmp_path)
        agents_dir = tmp_path / "aicouncil" / "agents"
        assert agents_dir.is_dir()
        assert list(agents_dir.iterdir()) == []

    def test_returns_aicouncil_path(self, tmp_path):
        result = ensure_scaffold(project_root=tmp_path)
        assert result == tmp_path / "aicouncil"

    def test_returns_existing_path(self, tmp_path):
        """Returns path even when directory already exists."""
        (tmp_path / "aicouncil").mkdir()
        result = ensure_scaffold(project_root=tmp_path)
        assert result == tmp_path / "aicouncil"

    def test_defaults_to_cwd(self, tmp_path, monkeypatch):
        """When no project_root given, uses cwd."""
        monkeypatch.chdir(tmp_path)
        result = ensure_scaffold()
        assert result == tmp_path / "aicouncil"
