from src.text_utils import normalize_slug

def test_basic_spaces():
    assert normalize_slug('Hello World') == 'hello-world'

def test_trim_and_collapse():
    assert normalize_slug('  A   B  ') == 'a-b'

def test_strip_punctuation():
    assert normalize_slug('Hello, World!') == 'hello-world'
