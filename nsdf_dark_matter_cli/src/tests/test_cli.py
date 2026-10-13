import os
import pytest
from typer.testing import CliRunner
from nsdf_dark_matter_cli.cli import app
from nsdf_dark_matter_cli.download import expand_prefix
from nsdf_dark_matter_cli import config
from typing import Dict

runner = CliRunner()


SAMPLE_DATASET = [
    ["07180808_1558_F0001", "48.123MiB", "R68"],
    ["07180808_1558_F0002", "188.189MiB", "R68"],
    ["07180808_1558_F0010", "151.993MiB", "R68"],
    ["07180808_1608_F0001", "50.837MiB", "R68"],
]


class TestExpandPrefix:
    def test_matches_all_series_files(self):
        assert expand_prefix("07180808_1558", SAMPLE_DATASET) == [
            "07180808_1558_F0001",
            "07180808_1558_F0002",
            "07180808_1558_F0010",
        ]

    def test_no_match_returns_empty(self):
        assert expand_prefix("99999999_9999", SAMPLE_DATASET) == []

    def test_empty_prefix_returns_empty(self):
        assert expand_prefix("", SAMPLE_DATASET) == []

    def test_full_identifier_matches_single_file(self):
        assert expand_prefix("07180808_1608_F0001", SAMPLE_DATASET) == ["07180808_1608_F0001"]


class TestDownloadCommand:
    def test_all_requires_prefix(self):
        """--all with no filename exits before touching the network"""
        result = runner.invoke(app, ["download", "--all"])

        assert result.exit_code == 1
        assert "Must provide a prefix" in result.stdout

    def test_all_unknown_prefix(self):
        """--all with a prefix that matches nothing exits before the network"""
        result = runner.invoke(app, ["download", "--all", "00000000_0000"])

        assert result.exit_code == 1
        assert "No files found matching prefix" in result.stdout


class TestConfigEndpoint:
    @pytest.fixture(autouse=True)
    def isolated_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "CONFIG_DIR", str(tmp_path))
        monkeypatch.setattr(config, "CONFIG_FILE", str(tmp_path / "config.json"))

    def test_default_endpoint(self):
        assert config.get_endpoint() == config.DEFAULT_ENDPOINT

    def test_set_and_get_endpoint(self):
        config.set_endpoint("https://example.com/api")

        assert config.get_endpoint() == "https://example.com/api"

    def test_invalid_endpoint_rejected(self):
        with pytest.raises(ValueError):
            config.set_endpoint("example.com/api")

    def test_config_command_sets_endpoint(self):
        result = runner.invoke(app, ["config", "--endpoint", "https://example.com/api"])

        assert result.exit_code == 0
        assert "Global endpoint set to" in result.stdout
        assert config.get_endpoint() == "https://example.com/api"

    def test_config_command_shows_endpoint(self):
        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert config.DEFAULT_ENDPOINT in result.stdout

    def test_reset_config_restores_defaults(self):
        config.set_endpoint("https://example.com/api")
        config.set_output_dir(str(config.CONFIG_DIR))

        config.reset_config()

        assert config.get_endpoint() == config.DEFAULT_ENDPOINT
        assert config.get_output_dir() == config.DEFAULT_CONFIG["output_dir"]

    def test_config_command_reset(self):
        config.set_endpoint("https://example.com/api")

        result = runner.invoke(app, ["config", "--reset"])

        assert result.exit_code == 0
        assert "Configuration reset to defaults" in result.stdout
        assert config.get_endpoint() == config.DEFAULT_ENDPOINT



@pytest.fixture
def golden_files() -> Dict[str, str]:
    return {
        "limit": os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "ls_lim_golden.txt")),
        "prefix": os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "ls_prefix_golden.txt")),
        "all": os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "ls_all_parameters_golden.txt"))
    }


class TestListCommand:
    def _compare_with_golden(self, result_bytes: bytes, golden_path: str):
        with open(golden_path, "rb") as f:
            golden_bytes = f.read()
        assert result_bytes == golden_bytes, f"Output differs from {golden_path}"

    def test_ls_limit(self, golden_files: Dict[str, str]):
        """Compare ls command with --limit against golden file"""
        result = runner.invoke(app, ["ls", "--limit", "5"])

        assert result.exit_code == 0

        result_bytes = result.stdout_bytes
        self._compare_with_golden(result_bytes, golden_files["limit"])

    def test_ls_prefix(self, golden_files: Dict[str, str]):
        """Compare ls command with --prefix against golden file"""
        result = runner.invoke(app, ["ls", "--prefix", "07220702_1055"])

        assert result.exit_code == 0

        result_bytes = result.stdout_bytes
        self._compare_with_golden(result_bytes, golden_files["prefix"])

    def test_all_parameters(self, golden_files: Dict[str, str]):
        """Compare ls command with --prefix against golden file"""
        result = runner.invoke(app, ["ls", "--prefix", "072", "--limit", "10"])

        assert result.exit_code == 0

        result_bytes = result.stdout_bytes
        self._compare_with_golden(result_bytes, golden_files["all"])
