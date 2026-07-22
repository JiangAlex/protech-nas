"""Tests for file management service functions."""

import os
import tempfile
import pytest
from src.services.file_service import (
    list_directory,
    make_directory,
    delete_item,
    move_item,
    copy_item,
    get_file_info,
)


@pytest.fixture
def tmp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some test files and dirs
        os.makedirs(os.path.join(tmpdir, "subdir"))
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("hello world")
        with open(os.path.join(tmpdir, "subdir", "nested.txt"), "w") as f:
            f.write("nested content")
        yield tmpdir


class TestListDirectory:
    def test_list_existing_dir(self, tmp_workspace):
        result = list_directory(tmp_workspace)
        assert result["success"] is True
        names = [i["name"] for i in result["items"]]
        assert "test.txt" in names
        assert "subdir" in names

    def test_list_nonexistent_dir(self):
        result = list_directory("/nonexistent/path/xyz123")
        assert result["success"] is False

    def test_items_have_required_fields(self, tmp_workspace):
        result = list_directory(tmp_workspace)
        for item in result["items"]:
            assert "name" in item
            assert "type" in item
            assert item["type"] in ("file", "dir")


class TestMakeDirectory:
    def test_create_new_dir(self, tmp_workspace):
        new_path = os.path.join(tmp_workspace, "newdir")
        result = make_directory(new_path)
        assert result["success"] is True
        assert os.path.isdir(new_path)

    def test_create_existing_dir_fails(self, tmp_workspace):
        existing = os.path.join(tmp_workspace, "subdir")
        result = make_directory(existing)
        assert result["success"] is False


class TestDeleteItem:
    def test_delete_file(self, tmp_workspace):
        path = os.path.join(tmp_workspace, "test.txt")
        result = delete_item(path)
        assert result["success"] is True
        assert not os.path.exists(path)

    def test_delete_directory(self, tmp_workspace):
        path = os.path.join(tmp_workspace, "subdir")
        result = delete_item(path)
        assert result["success"] is True
        assert not os.path.exists(path)

    def test_delete_nonexistent_fails(self, tmp_workspace):
        result = delete_item(os.path.join(tmp_workspace, "nope.txt"))
        assert result["success"] is False


class TestMoveItem:
    def test_move_file(self, tmp_workspace):
        src = os.path.join(tmp_workspace, "test.txt")
        dst = os.path.join(tmp_workspace, "moved.txt")
        result = move_item(src, dst)
        assert result["success"] is True
        assert not os.path.exists(src)
        assert os.path.exists(dst)

    def test_move_nonexistent_fails(self, tmp_workspace):
        result = move_item(os.path.join(tmp_workspace, "nope"), os.path.join(tmp_workspace, "dest"))
        assert result["success"] is False


class TestCopyItem:
    def test_copy_file(self, tmp_workspace):
        src = os.path.join(tmp_workspace, "test.txt")
        dst = os.path.join(tmp_workspace, "copy.txt")
        result = copy_item(src, dst)
        assert result["success"] is True
        assert os.path.exists(src)  # Original still exists
        assert os.path.exists(dst)

    def test_copy_nonexistent_fails(self, tmp_workspace):
        result = copy_item(os.path.join(tmp_workspace, "nope"), os.path.join(tmp_workspace, "dest"))
        assert result["success"] is False


class TestGetFileInfo:
    def test_file_info(self, tmp_workspace):
        path = os.path.join(tmp_workspace, "test.txt")
        result = get_file_info(path)
        assert result["success"] is True
        assert result["name"] == "test.txt"
        assert result["type"] == "file"
        assert result["size"] == 11  # "hello world"

    def test_dir_info(self, tmp_workspace):
        result = get_file_info(os.path.join(tmp_workspace, "subdir"))
        assert result["success"] is True
        assert result["type"] == "dir"

    def test_nonexistent_fails(self, tmp_workspace):
        result = get_file_info(os.path.join(tmp_workspace, "nope"))
        assert result["success"] is False
