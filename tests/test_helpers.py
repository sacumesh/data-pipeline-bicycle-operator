import tempfile
import os
from tools.cycling_stats import CyclingStats


def make_temp_xml(content: str):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(content)
        return f.name


def test_find_text_default_namespace():
    xml = '''<?xml version="1.0"?>
<CyclingDB xmlns="http://example.com/cycling">
  <outer>
    <inner>hello</inner>
  </outer>
</CyclingDB>
'''
    path = make_temp_xml(xml)
    try:
        s = CyclingStats(path)
        assert s._find_text(s.root, 'inner') == 'hello'
    finally:
        os.unlink(path)


def test_find_text_no_namespace():
    xml = '''<?xml version="1.0"?>
<CyclingDB>
  <outer>
    <inner>hi</inner>
  </outer>
</CyclingDB>
'''
    path = make_temp_xml(xml)
    try:
        s = CyclingStats(path)
        assert s._find_text(s.root, 'inner') == 'hi'
    finally:
        os.unlink(path)


def test_findall_nested_participants_default_ns():
    xml = '''<?xml version="1.0"?>
<CyclingDB xmlns="http://example.com/cycling">
  <tripGroups>
    <tripGroup>
      <participants>
        <participant>c1</participant>
        <participant>c2</participant>
      </participants>
    </tripGroup>
  </tripGroups>
</CyclingDB>
'''
    path = make_temp_xml(xml)
    try:
        s = CyclingStats(path)
        assert s.trip_groups is not None
        parts = s._findall(s.trip_groups, 'participant')
        assert len(parts) == 2
        assert [p.text for p in parts] == ['c1', 'c2']
    finally:
        os.unlink(path)


def test_find_nonexistent_returns_none_or_empty():
    xml = '<?xml version="1.0"?><CyclingDB></CyclingDB>'
    path = make_temp_xml(xml)
    try:
        s = CyclingStats(path)
        assert s._find_text(s.root, 'nope') is None
        assert s._findall(s.root, 'nope') == []
    finally:
        os.unlink(path)
