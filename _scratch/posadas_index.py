from pathlib import Path

for path in sorted(Path('/tmp/posadas').glob('*.txt'), key=lambda p: int(p.stem)):
    text = path.read_text(encoding='utf-8')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    print(f'{path.stem:>2} | {lines[0][:120] if lines else "(vacío)"} | {len(text)} chars')
