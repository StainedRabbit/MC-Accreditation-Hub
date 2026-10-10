"""Check slide, notes, PDF, screenshot, and decision coverage for the class package."""
import json
import posixpath
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from pypdf import PdfReader
from PIL import Image

from deck_content import SLIDES


here = Path(__file__).resolve().parent
pptx = here / 'MC_Accreditation_Hub_MIT007.pptx'
pdf = here / 'MC_Accreditation_Hub_MIT007.pdf'
manifest = json.loads((here / 'slide_manifest.json').read_text(encoding='utf-8'))
assert len(SLIDES) == len(manifest) == 53
assert set(re.findall(r'\bD\d{2}\b', '\n'.join(s['title'] + '\n' + '\n'.join(s['bullets'])
                                                   for s in SLIDES if s['kind'] == 'decisions'))) == {
    f'D{i:02}' for i in range(1, 23)}

ns = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
with ZipFile(pptx) as archive:
    assert archive.testzip() is None
    names = set(archive.namelist())
    for name in names:
        if name.endswith(('.xml', '.rels')):
            ET.fromstring(archive.read(name))
    presentation = ET.fromstring(archive.read('ppt/presentation.xml'))
    size = presentation.find('p:sldSz', ns)
    assert abs(int(size.get('cx')) / int(size.get('cy')) - 16 / 9) < .001
    for index, slide in enumerate(SLIDES, 1):
        slide_path = f'ppt/slides/slide{index}.xml'
        note_path = f'ppt/notesSlides/notesSlide{index}.xml'
        assert slide_path in names and note_path in names
        slide_text = ' '.join((element.text or '') for element in ET.fromstring(
            archive.read(slide_path)).findall('.//a:t', ns))
        assert slide['title'] in slide_text, (index, slide['title'])
        note_text = '\n'.join((element.text or '') for element in ET.fromstring(
            archive.read(note_path)).findall('.//a:t', ns))
        assert all(item in note_text for item in ('Point:', 'Source:', 'Limit:', 'Transition:')), index
        rel_path = f'ppt/slides/_rels/slide{index}.xml.rels'
        for rel in ET.fromstring(archive.read(rel_path)).findall('rel:Relationship', ns):
            target = posixpath.normpath(posixpath.join('ppt/slides', rel.get('Target')))
            assert target in names, (index, target)

reader = PdfReader(pdf)
assert len(reader.pages) == len(SLIDES)
for index, slide in enumerate(SLIDES):
    extracted = reader.pages[index].extract_text()
    assert slide['title'] in extracted, (index + 1, slide['title'])

screenshots = sorted((here / 'screenshots').glob('*.png'))
full = sorted((here / 'screenshots/full').glob('*.png'))
assert len(screenshots) == len(full) == 20
for path in screenshots + full:
    with Image.open(path) as image:
        assert image.width >= 1000 and image.height >= 700
        assert all(image.convert('RGB').getpixel((x, 0)) == (11, 37, 69)
                   for x in (0, image.width // 2, image.width - 1)), path

print(f'Validated {len(SLIDES)} 16:9 editable slides, notes, PDF pages, D01–D22, and 40 labeled screenshots.')
