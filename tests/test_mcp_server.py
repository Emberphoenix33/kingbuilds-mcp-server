import pytest
import tempfile
import os
import asyncio
from pathlib import Path

from mcp_server.security import safe_resolve_path, SecurityError
from mcp_server.config import Settings
from mcp_server.tools.files import register as register_files
from mcp_server.tools.web import register as register_web
from mcp_server.tools.transform import register as register_transform
from mcp_server.tools.http_request import register as register_http
from mcp_server.app import create_server
from mcp.server.fastmcp import FastMCP


class TestSecurity:
    def test_safe_resolve_path_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(allowed_dir=tmpdir)
            resolved = safe_resolve_path(Path(tmpdir), "test.txt")
            assert str(resolved) == os.path.join(tmpdir, "test.txt")

    def test_safe_resolve_path_blocks_traversal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(allowed_dir=tmpdir)
            with pytest.raises(SecurityError):
                safe_resolve_path(Path(tmpdir), "../../../etc/passwd")

    def test_safe_resolve_path_absolute_allowed(self):
        """Absolute paths are treated as relative to sandbox root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(allowed_dir=tmpdir)
            resolved = safe_resolve_path(Path(tmpdir), "/etc/passwd")
            assert str(resolved) == os.path.join(tmpdir, "etc/passwd")

    def test_safe_resolve_path_symlink_within_sandbox(self):
        """Symlinks that resolve within sandbox are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(allowed_dir=tmpdir)
            target = os.path.join(tmpdir, "target")
            os.makedirs(target)
            link = os.path.join(tmpdir, "link")
            os.symlink(target, link)
            resolved = safe_resolve_path(Path(tmpdir), "link/../etc/passwd")
            assert str(resolved) == os.path.join(tmpdir, "etc/passwd")


class TestFileOperations:
    @pytest.fixture
    def settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Settings(allowed_dir=tmpdir)

    def test_read_write_roundtrip(self, settings):
        import asyncio
        
        mcp = FastMCP("test")
        register_files(mcp, settings)
        
        async def run_test():
            # Write
            result = await mcp.call_tool("write_file", {"path": "test.txt", "content": "Hello, World!"})
            if isinstance(result, tuple):
                result = result[1]
            assert "error" not in result
            
            # Read
            result = await mcp.call_tool("read_file", {"path": "test.txt"})
            if isinstance(result, tuple):
                result = result[1]
            assert "error" not in result
            assert result["content"] == "Hello, World!"
        
        asyncio.run(run_test())

    def test_write_blocks_outside_sandbox(self, settings):
        import asyncio
        
        mcp = FastMCP("test")
        register_files(mcp, settings)
        
        async def run_test():
            result = await mcp.call_tool("write_file", {"path": "../../../etc/passwd", "content": "bad"})
            if isinstance(result, tuple):
                result = result[1]
            assert "error" in result
        
        asyncio.run(run_test())

    def test_list_directory(self, settings):
        import asyncio
        
        mcp = FastMCP("test")
        register_files(mcp, settings)
        
        async def run_test():
            await mcp.call_tool("write_file", {"path": "file1.txt", "content": "content1"})
            await mcp.call_tool("write_file", {"path": "file2.txt", "content": "content2"})
            
            result = await mcp.call_tool("list_directory", {"path": "."})
            if isinstance(result, tuple):
                result = result[1]
            assert "entries" in result
            assert len(result["entries"]) == 2
        
        asyncio.run(run_test())


class TestWebScraping:
    def test_scrape_basic(self):
        mcp = FastMCP("test")
        settings = Settings(allowed_dir="/tmp")
        register_web(mcp, settings)
        # This test would need mocking
        pass


class TestDataTransform:
    def test_json_to_csv(self):
        mcp = FastMCP("test")
        settings = Settings(allowed_dir="/tmp")
        
        from mcp_server.tools.transform import register as register_transform
        register_transform(mcp, settings)
        
        import asyncio
        import json
        
        async def run_test():
            data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
            result = await mcp.call_tool("transform_data", {"data": json.dumps(data), "input_format": "json", "operation": "convert", "output_format": "csv"})
            if isinstance(result, tuple):
                result = result[1]
            assert "a,b" in result.get("result", "")
        
        asyncio.run(run_test())
        
    def test_aggregation(self):
        mcp = FastMCP("test")
        settings = Settings(allowed_dir="/tmp")
        
        from mcp_server.tools.transform import register as register_transform
        register_transform(mcp, settings)
        
        import asyncio
        
        async def run_test():
            data = [1, 2, 3, 4, 5]
            result = await mcp.call_tool("transform_data", {"data": str(data), "input_format": "json", "operation": "sum"})
            if isinstance(result, tuple):
                result = result[1]
            assert result.get("result") == 15
        
        asyncio.run(run_test())


class TestServerFactory:
    def test_create_server(self):
        settings = Settings(allowed_dir="/tmp")
        mcp = create_server(settings)
        assert mcp is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])