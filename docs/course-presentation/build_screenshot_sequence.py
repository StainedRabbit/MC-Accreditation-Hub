"""Build a local-file-only screenshot walkthrough for service outage fallback."""
from pathlib import Path
from html import escape


here = Path(__file__).resolve().parent
shots = sorted((here / 'screenshots').glob('*.png'))
if len(shots) != 20:
    raise RuntimeError(f'Expected 20 fictional capture images, found {len(shots)}')
items = []
for index, path in enumerate(shots, 1):
    title = path.stem.split('-', 1)[1].replace('-', ' ').title()
    items.append(f'<section id="step-{index}"><h2>{index:02}. {escape(title)}</h2>'
                 f'<img src="screenshots/{escape(path.name)}" alt="Fictional local demonstration: {escape(title)}">'
                 f'<p><a href="screenshots/full/{escape(path.name)}">Open full-page copy</a></p></section>')
html = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>MIT 007 fictional local walkthrough</title>
<style>body{font-family:Arial,sans-serif;max-width:1200px;margin:auto;padding:26px;color:#14263D;background:#F6F8FB}
h1,h2{color:#0B2545}h1{border-top:8px solid #0F9E92;padding-top:20px}section{padding:24px 0;border-bottom:2px solid #D6E2E9}
img{max-width:100%;height:auto;border:1px solid #D6E2E9;box-shadow:0 4px 18px #2339}
a{color:#087A73}nav a{display:inline-block;padding:8px}</style></head><body>
<h1>MC Accreditation Hub · Fictional local demonstration</h1><p>Offline screenshot fallback, captured from a local course fixture. The simulated scanner is not an institutional malware scan.</p>
<nav>''' + ''.join(f'<a href="#step-{i}">{i:02}</a>' for i in range(1, 21)) + '</nav>' + ''.join(items) + '</body></html>'
(here / 'SCREENSHOT_SEQUENCE.html').write_text(html, encoding='utf-8')
print('Built offline sequence for 20 labeled application screenshots.')
