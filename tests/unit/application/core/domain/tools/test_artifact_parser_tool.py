import pytest
from software_factory_poc.application.core.domain.agents.scaffolding.tools.artifact_parser import ArtifactParser
from software_factory_poc.application.core.ports.gateways.dtos import FileContentDTO

class TestArtifactParserTool:
    def test_parse_response_multiple_files(self):
        # Setup
        response = """
Here is the code:

<<<FILE:src/main.py>>>
print("Hello")
<<<END>>>

Some explanation.

<<<FILE:README.md>>>
# Title
<<<END>>>
"""
        tool = ArtifactParser()
        
        # Act
        files = tool.parse_response(response)
        
        # Assert
        assert len(files) == 2
        assert files[0].path == "src/main.py"
        assert files[0].content.strip() == 'print("Hello")'
        assert files[1].path == "README.md"
        assert files[1].content.strip() == '# Title'
        assert isinstance(files[0], FileContentDTO)

    def test_parse_response_empty(self):
        tool = ArtifactParser()
        files = tool.parse_response("No files here.")
        assert len(files) == 0

    def test_parse_response_ignores_invalid_paths(self):
        response = """
<<<FILE:../hack.py>>>
import os
<<<END>>>
<<<FILE:safe.py>>>
ok
<<<END>>>
"""
        tool = ArtifactParser()
        files = tool.parse_response(response)
        assert len(files) == 1
        assert files[0].path == "safe.py"
