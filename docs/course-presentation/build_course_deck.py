"""Create the editable course PPTX and matching print HTML from checked slide content.

The bundled Artifact Tool is unavailable in this Windows workspace, so this
builder writes ordinary Office Open XML parts using the supplied PPTX package's
master/theme as a base. Every title, body, footer, diagram line, and decision
row is an editable PowerPoint text shape; screenshots are embedded images.
"""
from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from deck_content import SLIDES


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'docs' / 'MC_Accreditation_Hub.pptx'
OUTPUT = HERE / 'MC_Accreditation_Hub_MIT007.pptx'
PRINT_HTML = HERE / 'MC_Accreditation_Hub_MIT007.html'
SHOT = HERE / 'screenshots'
EMU = 9525
W, H = 1280, 720
NAVY, TEAL, INK, MUTED, LIGHT, WHITE = '0B2545', '0F9E92', '14263D', '486078', 'F6F8FB', 'FFFFFF'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
for prefix, ns in [('p', P), ('a', A), ('r', R)]:
    ET.register_namespace(prefix, ns)


def q(ns, tag):
    return f'{{{ns}}}{tag}'


def xml_bytes(element):
    return ET.tostring(element, encoding='utf-8', xml_declaration=True)


def box(sp_tree, ident, name, x, y, width, height, text='', *, size=23, color=INK,
        bold=False, fill=None, align='l', margin=0, border=None):
    sp = ET.SubElement(sp_tree, q(P, 'sp'))
    nv = ET.SubElement(sp, q(P, 'nvSpPr'))
    ET.SubElement(nv, q(P, 'cNvPr'), {'id': str(ident), 'name': name})
    ET.SubElement(nv, q(P, 'cNvSpPr'), {'txBox': '1'})
    ET.SubElement(nv, q(P, 'nvPr'))
    sppr = ET.SubElement(sp, q(P, 'spPr'))
    xfrm = ET.SubElement(sppr, q(A, 'xfrm'))
    ET.SubElement(xfrm, q(A, 'off'), {'x': str(round(x * EMU)), 'y': str(round(y * EMU))})
    ET.SubElement(xfrm, q(A, 'ext'), {'cx': str(round(width * EMU)), 'cy': str(round(height * EMU))})
    geom = ET.SubElement(sppr, q(A, 'prstGeom'), {'prst': 'rect'})
    ET.SubElement(geom, q(A, 'avLst'))
    if fill:
        ET.SubElement(ET.SubElement(sppr, q(A, 'solidFill')), q(A, 'srgbClr'), {'val': fill})
    else:
        ET.SubElement(sppr, q(A, 'noFill'))
    line = ET.SubElement(sppr, q(A, 'ln'), {'w': '9525' if border else '0'})
    if border:
        ET.SubElement(ET.SubElement(line, q(A, 'solidFill')), q(A, 'srgbClr'), {'val': border})
    else:
        ET.SubElement(line, q(A, 'noFill'))
    tx = ET.SubElement(sp, q(P, 'txBody'))
    ET.SubElement(tx, q(A, 'bodyPr'), {'wrap': 'square', 'anchor': 't',
                                      'lIns': str(margin * EMU), 'rIns': str(margin * EMU),
                                      'tIns': str(margin * EMU), 'bIns': str(margin * EMU)})
    ET.SubElement(tx, q(A, 'lstStyle'))
    for line_text in str(text).split('\n'):
        para = ET.SubElement(tx, q(A, 'p'))
        ET.SubElement(para, q(A, 'pPr'), {'algn': align})
        run = ET.SubElement(para, q(A, 'r'))
        rp = ET.SubElement(run, q(A, 'rPr'), {'lang': 'en-US', 'sz': str(round(size * 100)),
                                            'b': '1' if bold else '0'})
        ET.SubElement(ET.SubElement(rp, q(A, 'solidFill')), q(A, 'srgbClr'), {'val': color})
        ET.SubElement(rp, q(A, 'latin'), {'typeface': 'Aptos'})
        ET.SubElement(run, q(A, 't')).text = line_text
        ET.SubElement(para, q(A, 'endParaRPr'), {'lang': 'en-US'})
    return sp


def picture(sp_tree, ident, name, x, y, width, height, rel_id):
    pic = ET.SubElement(sp_tree, q(P, 'pic'))
    nv = ET.SubElement(pic, q(P, 'nvPicPr'))
    ET.SubElement(nv, q(P, 'cNvPr'), {'id': str(ident), 'name': name,
                                     'descr': 'Fictional local application screenshot'})
    c = ET.SubElement(nv, q(P, 'cNvPicPr'))
    ET.SubElement(c, q(A, 'picLocks'), {'noChangeAspect': '1'})
    ET.SubElement(nv, q(P, 'nvPr'))
    bf = ET.SubElement(pic, q(P, 'blipFill'))
    ET.SubElement(bf, q(A, 'blip'), {q(R, 'embed'): rel_id})
    ET.SubElement(ET.SubElement(bf, q(A, 'stretch')), q(A, 'fillRect'))
    sppr = ET.SubElement(pic, q(P, 'spPr'))
    xf = ET.SubElement(sppr, q(A, 'xfrm'))
    ET.SubElement(xf, q(A, 'off'), {'x': str(round(x * EMU)), 'y': str(round(y * EMU))})
    ET.SubElement(xf, q(A, 'ext'), {'cx': str(round(width * EMU)), 'cy': str(round(height * EMU))})
    ET.SubElement(ET.SubElement(sppr, q(A, 'prstGeom'), {'prst': 'rect'}), q(A, 'avLst'))


def slide_xml(slide, number, count):
    cover = slide['kind'] in ('cover', 'closing')
    root = ET.Element(q(P, 'sld'))
    csld = ET.SubElement(root, q(P, 'cSld'), {'name': f'{number:02} {slide["title"]}'})
    bg = ET.SubElement(csld, q(P, 'bg'))
    bgpr = ET.SubElement(bg, q(P, 'bgPr'))
    ET.SubElement(ET.SubElement(bgpr, q(A, 'solidFill')), q(A, 'srgbClr'),
                  {'val': NAVY if cover else LIGHT})
    tree = ET.SubElement(csld, q(P, 'spTree'))
    nv = ET.SubElement(tree, q(P, 'nvGrpSpPr'))
    ET.SubElement(nv, q(P, 'cNvPr'), {'id': '1', 'name': ''})
    ET.SubElement(nv, q(P, 'cNvGrpSpPr'))
    ET.SubElement(nv, q(P, 'nvPr'))
    gp = ET.SubElement(tree, q(P, 'grpSpPr'))
    xfrm = ET.SubElement(gp, q(A, 'xfrm'))
    for tag, attrs in [('off', {'x': '0', 'y': '0'}), ('ext', {'cx': '0', 'cy': '0'}),
                       ('chOff', {'x': '0', 'y': '0'}), ('chExt', {'cx': '0', 'cy': '0'})]:
        ET.SubElement(xfrm, q(A, tag), attrs)
    ident = 2
    def b(name, x, y, w, h, text, **kw):
        nonlocal ident
        box(tree, ident, name, x, y, w, h, text, **kw)
        ident += 1
    if cover:
        b('Accent rule', 0, 0, W, 14, '', fill=TEAL)
        b('Course label', 70, 65, 900, 42, slide['bullets'][0] if slide['bullets'] else 'MIT 007',
          size=21, color='71E0D3', bold=True)
        b('Title', 68, 175, 1140, 130, slide['title'], size=58, color=WHITE, bold=True)
        b('Subtitle', 71, 326, 1100, 150, slide['lead'], size=30, color='E4EFF4')
        b('Attribution', 72, 550, 1080, 75, '\n'.join(slide['bullets'][1:]), size=21, color='BED5E4')
    else:
        b('Accent rule', 0, 0, W, 13, '', fill=TEAL)
        b('Section', 52, 34, 850, 32, slide['section'].upper(), size=17, color=TEAL, bold=True)
        b('Status', 925, 32, 300, 32, slide['status'], size=16, color=MUTED, align='r')
        b('Title', 52, 82, 1170, 75, slide['title'], size=42, color=NAVY, bold=True)
        b('Lead', 55, 163, 1160, 77, slide['lead'], size=23, color=INK)
        if slide['kind'] == 'architecture':
            for title, detail, x, y, w, h in [
                ('BROWSER', 'React · Vite · TypeScript\nSession + CSRF', 60, 290, 275, 195),
                ('APPLICATION API', 'Django REST Framework\nScope + workflow + audit', 425, 290, 340, 195),
                ('POSTGRESQL', 'Relational records\nHistory + constraints', 895, 255, 300, 120),
                ('PRIVATE MEDIA', 'Versioned bytes\nProtected downloads', 895, 405, 300, 120),
            ]:
                b(f'{title} panel', x, y, w, h, '', fill='E4EFF4', border='D6E2E9')
                b(f'{title} heading', x + 16, y + 20, w - 32, 38, title, size=21, color=NAVY, bold=True)
                b(f'{title} detail', x + 16, y + 65, w - 32, h - 72, detail, size=18, color=INK)
            b('Browser to API', 350, 352, 67, 70, '→', size=42, color=TEAL, bold=True)
            b('API to database', 790, 302, 90, 60, '→', size=42, color=TEAL, bold=True)
            b('API to media', 790, 445, 90, 60, '→', size=42, color=TEAL, bold=True)
            b('Architecture boundary', 62, 555, 1120, 65,
              'Django authorizes every metadata query and file response; no public evidence route.', size=21)
        elif slide['kind'] == 'table':
            widths = [170, 217, 217, 217, 349] if slide['title'].startswith('Role') else [185, 245, 385, 355]
            rows = [list(map(str.strip, line.split('|'))) for line in slide['bullets']]
            for row_index, row in enumerate(rows):
                x = 55
                y = 252 + row_index * 55
                for col_index, (value, width) in enumerate(zip(row, widths)):
                    head = row_index == 0
                    b(f'Table r{row_index} c{col_index}', x, y, width, 53, value,
                      size=17 if head else 16, color=WHITE if head else INK,
                      bold=head or col_index == 0,
                      fill=NAVY if head else ('FFFFFF' if row_index % 2 else 'EAF2F5'),
                      border='D6E2E9', margin=8)
                    x += width
        elif slide['image']:
            picture(tree, ident, 'Actual fictional application screenshot', 55, 248, 715, 401, 'rId3')
            ident += 1
            for j, item in enumerate(slide['bullets'][:4]):
                b(f'Explanation {j+1}', 817, 258 + j * 92, 390, 84, '• ' + item, size=19, color=INK)
        elif slide['kind'] == 'decisions':
            for j, item in enumerate(slide['bullets']):
                match = re.match(r'^(D\d\d)\s+(.*?)\s+\|\s+(.*?)\s+\|\s+(.*?)\s+\|\s+(.*)$', item)
                if not match:
                    continue
                code, topic, state, owners, gate = match.groups()
                y = 245 + j * 79
                b(f'{code} code', 58, y, 88, 50, code, size=23, color=TEAL, bold=True)
                b(f'{code} topic', 150, y, 440, 50, topic, size=22, color=NAVY, bold=True)
                b(f'{code} state', 605, y, 280, 50, state, size=18, color=MUTED)
                b(f'{code} owners', 910, y, 320, 50, owners, size=16, color=MUTED)
                b(f'{code} gate', 150, y + 37, 1055, 42, gate, size=17, color=INK)
        else:
            y = 257
            for j, item in enumerate(slide['bullets']):
                width = 1140
                approx_lines = max(1, math.ceil(len(item) / 92))
                height = max(56, 28 * approx_lines + 20)
                b(f'Point {j+1}', 70, y, width, height, '•  ' + item, size=22 if len(slide['bullets']) < 6 else 20,
                  color=INK)
                y += height + 12
        b('Footer rule', 52, 665, 1172, 2, '', fill='D6E2E9')
        b('Footer', 53, 676, 1010, 29, 'MC Accreditation Hub  ·  MIT 007  ·  Fictional local evidence unless marked otherwise',
          size=13, color=MUTED)
        b('Page', 1110, 676, 120, 29, f'{number:02} / {count:02}', size=13, color=MUTED, align='r')
    ET.SubElement(root, q(P, 'clrMapOvr')).append(ET.Element(q(A, 'masterClrMapping')))
    return xml_bytes(root)


def note_xml(template, notes, number):
    root = ET.fromstring(template)
    for shape in root.findall(f'.//{q(P,"sp")}'):
        placeholder = shape.find(f'./{q(P,"nvSpPr")}/{q(P,"nvPr")}/{q(P,"ph")}')
        if placeholder is None:
            continue
        if placeholder.get('type') == 'body':
            tx = shape.find(q(P, 'txBody'))
            for child in list(tx):
                if child.tag == q(A, 'p'):
                    tx.remove(child)
            for line in notes.splitlines():
                para = ET.SubElement(tx, q(A, 'p'))
                run = ET.SubElement(para, q(A, 'r'))
                ET.SubElement(run, q(A, 'rPr'), {'lang': 'en-US', 'sz': '1200'})
                ET.SubElement(run, q(A, 't')).text = line
        if placeholder.get('type') == 'sldNum':
            for text in shape.findall(f'.//{q(A,"t")}'):
                text.text = str(number)
    return xml_bytes(root)


def relationship_root(entries):
    root = ET.Element(q(REL, 'Relationships'))
    for ident, kind, target in entries:
        ET.SubElement(root, q(REL, 'Relationship'), {'Id': ident, 'Type': R + '/' + kind, 'Target': target})
    return xml_bytes(root)


def build_pptx():
    count = len(SLIDES)
    with ZipFile(SOURCE) as original:
        parts = {name: original.read(name) for name in original.namelist()
                 if not re.fullmatch(r'ppt/slides/(?:_rels/)?slide\d+\.xml(?:\.rels)?', name)
                 and not re.fullmatch(r'ppt/notesSlides/(?:_rels/)?notesSlide\d+\.xml(?:\.rels)?', name)}
        notes_template = original.read('ppt/notesSlides/notesSlide1.xml')
    presentation = ET.fromstring(parts['ppt/presentation.xml'])
    ids = presentation.find(q(P, 'sldIdLst'))
    ids.clear()
    for i in range(1, count + 1):
        ET.SubElement(ids, q(P, 'sldId'), {'id': str(255 + i), q(R, 'id'): f'rId{i+1}'})
    notes_master = presentation.find(q(P, 'notesMasterIdLst')).find(q(P, 'notesMasterId'))
    notes_master.set(q(R, 'id'), f'rId{count+2}')
    parts['ppt/presentation.xml'] = xml_bytes(presentation)
    pres_rels = [('rId1', 'slideMaster', 'slideMasters/slideMaster1.xml')]
    pres_rels += [(f'rId{i+1}', 'slide', f'slides/slide{i}.xml') for i in range(1, count + 1)]
    pres_rels += [(f'rId{count+2}', 'notesMaster', 'notesMasters/notesMaster1.xml'),
                  (f'rId{count+3}', 'presProps', 'presProps.xml'),
                  (f'rId{count+4}', 'viewProps', 'viewProps.xml'),
                  (f'rId{count+5}', 'theme', 'theme/theme1.xml'),
                  (f'rId{count+6}', 'tableStyles', 'tableStyles.xml')]
    parts['ppt/_rels/presentation.xml.rels'] = relationship_root(pres_rels)
    types = ET.fromstring(parts['[Content_Types].xml'])
    for entry in list(types):
        part = entry.get('PartName', '')
        if re.fullmatch(r'/ppt/(?:slides/slide|notesSlides/notesSlide)\d+\.xml', part):
            types.remove(entry)
    for i in range(1, count + 1):
        ET.SubElement(types, q(CT, 'Override'), {'PartName': f'/ppt/slides/slide{i}.xml',
            'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'})
        ET.SubElement(types, q(CT, 'Override'), {'PartName': f'/ppt/notesSlides/notesSlide{i}.xml',
            'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml'})
    parts['[Content_Types].xml'] = xml_bytes(types)
    app = ET.fromstring(parts['docProps/app.xml'])
    for entry in app.iter():
        if entry.tag.endswith('}Slides'):
            entry.text = str(count)
    parts['docProps/app.xml'] = xml_bytes(app)
    for i, slide in enumerate(SLIDES, 1):
        parts[f'ppt/slides/slide{i}.xml'] = slide_xml(slide, i, count)
        rels = [('rId1', 'slideLayout', '../slideLayouts/slideLayout1.xml'),
                ('rId2', 'notesSlide', f'../notesSlides/notesSlide{i}.xml')]
        if slide['image']:
            src = SHOT / slide['image']
            if not src.is_file():
                raise FileNotFoundError(src)
            media_name = f'course_{i:02}.png'
            parts[f'ppt/media/{media_name}'] = src.read_bytes()
            rels.append(('rId3', 'image', f'../media/{media_name}'))
        parts[f'ppt/slides/_rels/slide{i}.xml.rels'] = relationship_root(rels)
        parts[f'ppt/notesSlides/notesSlide{i}.xml'] = note_xml(notes_template, slide['notes'], i)
        parts[f'ppt/notesSlides/_rels/notesSlide{i}.xml.rels'] = relationship_root([
            ('rId1', 'notesMaster', '../notesMasters/notesMaster1.xml'),
            ('rId2', 'slide', f'../slides/slide{i}.xml')])
    with ZipFile(OUTPUT, 'w', compression=ZIP_DEFLATED, compresslevel=7) as output:
        for name, payload in parts.items():
            output.writestr(name, payload)


def build_html():
    sections = []
    for i, slide in enumerate(SLIDES, 1):
        cover = slide['kind'] in ('cover', 'closing')
        if cover:
            body = (f'<div class="cover-label">{html.escape(slide["bullets"][0])}</div>'
                    f'<h1>{html.escape(slide["title"])}</h1><p class="cover-lead">{html.escape(slide["lead"])}</p>'
                    f'<div class="cover-footer">{"<br>".join(html.escape(x) for x in slide["bullets"][1:])}</div>')
        else:
            if slide['kind'] == 'architecture':
                cards = [('BROWSER', 'React · Vite · TypeScript<br>Session + CSRF'),
                         ('APPLICATION API', 'Django REST Framework<br>Scope + workflow + audit'),
                         ('POSTGRESQL', 'Relational records<br>History + constraints'),
                         ('PRIVATE MEDIA', 'Versioned bytes<br>Protected downloads')]
                content = ('<div class="architecture">' + ''.join(
                    f'<div class="arch-card arch-{j}"><b>{html.escape(title)}</b><p>{detail}</p></div>'
                    for j, (title, detail) in enumerate(cards))
                    + '<span class="arrow a1">→</span><span class="arrow a2">→</span>'
                    + '<span class="arrow a3">→</span>'
                    + '<div class="arch-caption">Django authorizes every metadata query and file response; no public evidence route.</div></div>')
            elif slide['kind'] == 'table':
                rows = [list(map(str.strip, line.split('|'))) for line in slide['bullets']]
                columns = '170px 217px 217px 217px 349px' if slide['title'].startswith('Role') else '185px 245px 385px 355px'
                content = '<div class="table-layout" style="--columns:' + columns + '">' + ''.join(
                    '<div class="table-row' + (' header' if j == 0 else '') + '">' + ''.join(
                        '<div>' + html.escape(cell) + '</div>' for cell in row) + '</div>'
                    for j, row in enumerate(rows)) + '</div>'
            elif slide['image']:
                content = (f'<div class="image-layout"><img src="screenshots/{html.escape(slide["image"])}">'
                           '<div class="image-points">' + ''.join(f'<p>• {html.escape(x)}</p>' for x in slide['bullets'][:4]) + '</div></div>')
            elif slide['kind'] == 'decisions':
                rows = []
                for line in slide['bullets']:
                    parts = [x.strip() for x in line.split('|')]
                    first = parts[0].split('  ', 1)
                    rows.append('<div class="decision"><strong>' + html.escape(first[0]) + '</strong><b>'
                                + html.escape(first[1]) + '</b><em>' + html.escape(parts[1])
                                + '</em><span>' + html.escape(parts[2]) + '</span><small>'
                                + html.escape(parts[3]) + '</small></div>')
                content = '<div class="decisions">' + ''.join(rows) + '</div>'
            else:
                content = '<div class="bullets">' + ''.join(f'<p>•&nbsp; {html.escape(x)}</p>' for x in slide['bullets']) + '</div>'
            body = (f'<div class="section">{html.escape(slide["section"].upper())}</div>'
                    f'<div class="status">{html.escape(slide["status"])}</div>'
                    f'<h2>{html.escape(slide["title"])}</h2>'
                    f'<p class="lead">{html.escape(slide["lead"])}</p>{content}'
                    f'<footer>MC Accreditation Hub · MIT 007 · Fictional local evidence unless marked otherwise'
                    f'<span>{i:02} / {len(SLIDES):02}</span></footer>')
        sections.append(f'<section class="slide {"cover" if cover else ""}">{body}</section>')
    css = '''
@page { size: 13.333in 7.5in; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: Aptos, Arial, sans-serif; color: #14263D; }
.slide { position: relative; width: 1280px; height: 720px; overflow: hidden; background: #F6F8FB;
         break-after: page; page-break-after: always; border-top: 13px solid #0F9E92; }
.section { position: absolute; top: 34px; left: 52px; color: #0F9E92; font-size: 17px; font-weight: 700; letter-spacing: 1.2px; }
.status { position: absolute; top: 34px; right: 56px; color: #486078; font-size: 16px; }
h2 { position: absolute; top: 77px; left: 52px; width: 1170px; margin: 0; color: #0B2545; font-size: 42px; line-height: 1.1; }
.lead { position: absolute; top: 159px; left: 55px; width: 1160px; margin: 0; font-size: 23px; line-height: 1.25; }
.bullets { position: absolute; top: 252px; left: 70px; width: 1140px; }
.bullets p { font-size: 22px; line-height: 1.38; margin: 0 0 21px 0; }
.image-layout { position: absolute; left: 55px; top: 248px; display: flex; gap: 47px; }
.image-layout img { width: 715px; height: 401px; object-fit: fill; border: 1px solid #D6E2E9; }
.image-points { width: 390px; }
.image-points p { font-size: 19px; line-height: 1.36; margin: 0 0 30px; }
.architecture { position: absolute; top: 255px; left: 55px; width: 1170px; height: 375px; }
.arch-card { position: absolute; background: #E4EFF4; border: 1px solid #D6E2E9; padding: 20px 16px; }
.arch-card b { font-size: 21px; color: #0B2545; }
.arch-card p { font-size: 18px; line-height: 1.5; }
.arch-0 { left: 5px; top: 35px; width: 275px; height: 195px; }
.arch-1 { left: 370px; top: 35px; width: 340px; height: 195px; }
.arch-2 { left: 840px; top: 0; width: 300px; height: 120px; }
.arch-3 { left: 840px; top: 150px; width: 300px; height: 120px; }
.arrow { position: absolute; color: #0F9E92; font-size: 48px; font-weight: bold; }
.a1 { left: 300px; top: 88px; }.a2 { left: 735px; top: 35px; }.a3 { left: 735px; top: 180px; }
.arch-caption { position: absolute; top: 300px; left: 7px; font-size: 21px; }
.table-layout { position: absolute; top: 252px; left: 55px; }
.table-row { display: grid; grid-template-columns: var(--columns); height: 55px; }
.table-row div { border: 1px solid #D6E2E9; padding: 8px; font-size: 16px; line-height: 1.15; background: #FFFFFF; }
.table-row:nth-child(odd) div { background: #EAF2F5; }
.table-row div:first-child { font-weight: 700; }
.table-row.header div { background: #0B2545; color: white; font-size: 17px; font-weight: 700; }
.decisions { position: absolute; top: 245px; left: 58px; width: 1170px; }
.decision { display: grid; grid-template-columns: 88px 450px 280px 330px; grid-template-rows: 34px 39px;
            border-bottom: 1px solid #D6E2E9; align-items: start; }
.decision strong { color: #0F9E92; font-size: 23px; }
.decision b { color: #0B2545; font-size: 22px; }
.decision em { font-style: normal; color: #486078; font-size: 18px; }
.decision span { color: #486078; font-size: 16px; }
.decision small { grid-column: 2 / 5; font-size: 17px; }
footer { position: absolute; left: 52px; top: 666px; width: 1172px; border-top: 2px solid #D6E2E9;
         padding-top: 10px; color: #486078; font-size: 13px; }
footer span { float: right; }
.cover { background: #0B2545; color: white; }
.cover-label { position: absolute; left: 70px; top: 65px; font-size: 21px; font-weight: 700; color: #71E0D3; }
h1 { position: absolute; top: 170px; left: 68px; width: 1140px; font-size: 58px; margin: 0; }
.cover-lead { position: absolute; top: 325px; left: 71px; width: 1100px; font-size: 30px; line-height: 1.3; margin: 0; color: #E4EFF4; }
.cover-footer { position: absolute; top: 550px; left: 72px; font-size: 21px; line-height: 1.5; color: #BED5E4; }
'''
    PRINT_HTML.write_text('<!doctype html><html><head><meta charset="utf-8"><style>' + css +
                          '</style></head><body>' + ''.join(sections) + '</body></html>', encoding='utf-8')


if __name__ == '__main__':
    build_pptx()
    build_html()
    (HERE / 'slide_manifest.json').write_text(json.dumps([
        {'number': i, 'title': s['title'], 'status': s['status'], 'source': s['source'], 'image': s['image']}
        for i, s in enumerate(SLIDES, 1)], indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Built {len(SLIDES)} editable PowerPoint slides and matching print HTML.')
