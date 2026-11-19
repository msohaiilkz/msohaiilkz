from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from patch_readme import patch, START, END

def test_preserves_existing_readme():
    original='# Existing Profile\n\nAll my 15 projects and their links stay here.\n'
    result=patch(original)
    assert result.endswith(original)
    assert result.count(START)==1 and result.count(END)==1
    assert patch(result)==result

def test_refuses_corrupt_markers():
    try:
        patch('hello '+START+' broken')
    except ValueError:
        return
    raise AssertionError('Expected safety validation error')

if __name__=='__main__':
    test_preserves_existing_readme();test_refuses_corrupt_markers();print('README patch safety tests passed')
