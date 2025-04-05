# tests/test_utils.py

import pytest
import re
import zipfile
import yaml
from pathlib import Path

from engine.utils.file import is_safe_path, extract_zip
from engine.utils.readable_uid import generate_readable_uid
from engine.utils.yaml import YAMLUtils, YAMLError

class TestFileUtil:

    def test_is_safe_path_valid(self, tmp_path: Path):
        base_path = tmp_path
        safe_file_path = "subdir/safe_file.txt"
        safe_nonexistent_path = "another_dir/new_file.txt"

        # Create necessary parent directory for the check
        (base_path / "subdir").mkdir()
        (base_path / "another_dir").mkdir()

        assert is_safe_path(base_path, safe_file_path) is True
        assert is_safe_path(base_path, safe_nonexistent_path) is True

    def test_is_safe_path_invalid(self, tmp_path: Path):
        base_path = tmp_path
        # Path traversal
        assert is_safe_path(base_path, "../outside.txt") is False
        assert is_safe_path(base_path, "subdir/../../outside.txt") is False
        # Absolute paths
        assert is_safe_path(base_path, "/etc/passwd") is False
        # Path starting with ..
        assert is_safe_path(base_path, "..\\secrets.txt") is False


    def test_extract_zip(self, tmp_path: Path):
        zip_content_dir = tmp_path / "zip_content"
        zip_content_dir.mkdir()
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        zip_path = tmp_path / "test.zip"

        # Create files and directories to zip
        file1_path = zip_content_dir / "file1.txt"
        file1_path.write_text("content1")
        subdir_path = zip_content_dir / "subdir"
        subdir_path.mkdir()
        file2_path = subdir_path / "file2.txt"
        file2_path.write_text("content2")

        # Create the zip file
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(file1_path, arcname="file1.txt")
            zipf.write(file2_path, arcname="subdir/file2.txt")

        # Extract the zip
        extract_zip(zip_path, extract_dir)

        # Verify extraction
        extracted_file1 = extract_dir / "file1.txt"
        extracted_file2 = extract_dir / "subdir" / "file2.txt"

        assert extracted_file1.exists()
        assert extracted_file1.read_text() == "content1"
        assert extracted_file2.exists()
        assert extracted_file2.read_text() == "content2"


class TestReadableUID:

    def test_generate_readable_uid_unique(self):
        uid1 = generate_readable_uid()
        uid2 = generate_readable_uid()
        assert uid1 != uid2


class TestYAMLUtils:

    def test_read_kit_success(self, tmp_path: Path):
        module_path = tmp_path / "test_module"
        module_path.mkdir()
        kit_yaml_path = module_path / "kit.yaml"
        sample_content = {"id": "test-kit", "version": "1.0.0", "name": "Test Kit"}
        kit_yaml_path.write_text(yaml.dump(sample_content))

        result = YAMLUtils.read_kit(module_path)
        assert result == sample_content

    def test_read_kit_not_found(self, tmp_path: Path):
        module_path = tmp_path / "nonexistent_module"
        # Don't create the directory or file

        with pytest.raises(YAMLError, match="kit.yaml not found"):
            YAMLUtils.read_kit(module_path)

    def test_read_kit_invalid_yaml(self, tmp_path: Path):
        module_path = tmp_path / "invalid_module"
        module_path.mkdir()
        kit_yaml_path = module_path / "kit.yaml"
        # Write invalid YAML (e.g., unclosed bracket)
        kit_yaml_path.write_text("id: test-kit\nversion: [1.0.0")

        with pytest.raises(YAMLError, match="Failed to parse kit.yaml"):
            YAMLUtils.read_kit(module_path)