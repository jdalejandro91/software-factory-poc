from software_factory_poc.application.core.domain.services.file_parsing_service import FileParsingService


def test_parse_valid_blocks():
    text = """
Some intro text
<<<FILE:main.py>>>
print("Hello World")
<<<END>>>

<<<FILE:utils/helper.py>>>
def help():
    pass
<<<END>>>
"""
    files = FileParsingService.parse_llm_response(text)
    assert len(files) == 2
    assert files[0].path == "main.py"
    assert files[0].content.strip() == 'print("Hello World")'
    assert files[1].path == "utils/helper.py"

def test_parse_ignores_invalid_paths():
    text = """
<<<FILE:../hack.py>>>
malicious code
<<<END>>>

<<<FILE:/etc/passwd>>>
root:x:0:0
<<<END>>>

<<<FILE:safe.py>>>
ok
<<<END>>>
"""
    files = FileParsingService.parse_llm_response(text)
    assert len(files) == 1
    assert files[0].path == "safe.py"

def test_parse_handles_empty_content():
    text = """
<<<FILE:empty.py>>>
<<<END>>>
"""
    files = FileParsingService.parse_llm_response(text)
    assert len(files) == 1
    assert "Empty file" in files[0].content

def test_parse_is_robust_to_spacing():
    text = """
<<<FILE:   spaced.py   >>>
content
<<<END>>>
"""
    files = FileParsingService.parse_llm_response(text)
    assert len(files) == 1
    assert files[0].path == "spaced.py"
