"""Visibly label the captured fictional local UI images for offline presentation."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


root = Path(__file__).resolve().parent.parent
directory = root / 'docs/course-presentation/screenshots'
font_path = Path(r'C:\Windows\Fonts\arialbd.ttf')
font = ImageFont.truetype(str(font_path), 18) if font_path.is_file() else ImageFont.load_default()
count = 0
for path in sorted(directory.rglob('*.png')):
    source = Image.open(path).convert('RGB')
    if source.width < 100 or source.height < 100:
        raise RuntimeError(f'Unexpected screenshot dimensions: {path}')
    # Capture overwrites these files before each labeling run. A uniform navy top
    # band also allows a direct repeat of this script without stacking labels.
    if all(source.getpixel((x, 0)) == (11, 37, 69) for x in (0, source.width // 2, source.width - 1)):
        continue
    output = Image.new('RGB', (source.width, source.height + 38), (11, 37, 69))
    output.paste(source, (0, 38))
    ImageDraw.Draw(output).text((14, 8), 'FICTIONAL LOCAL DEMONSTRATION', font=font, fill=(255, 255, 255))
    output.save(path, optimize=True)
    count += 1
print(f'Labeled {count} fictional local screenshot files.')
