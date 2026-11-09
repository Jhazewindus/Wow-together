"""Check that the optional Gold module only uses the versioned core interface."""
import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {
    'GoldAPIVersion', 'RegisterModule', 'FindTravelPath', 'TravelPointDistance',
    'PlayerPoint', 'TrailLoop', 'RouteCostModel', 'PushGuideStop',
    'ClearModuleStops', 'RegisterSyncKind', 'CatalogueQuest', 'catalogue',
    'ReadPublic', 'Public', 'GuideInteger', 'SafeTitle', 'Option', 'SetOption',
    'Print', 'On', 'ResearchExportHook', 'Gold', 'STEP_SYMBOLS',
}
ACCESS = re.compile(r'\bns\s*(?:\.\s*([A-Za-z_]\w*)|\[\s*(["\'])([A-Za-z_]\w*)\2\s*\])')
DYNAMIC = re.compile(r'\bns\s*\[')
ALIAS = re.compile(r'\b(?:local\s+)?([A-Za-z_]\w*)\s*=\s*ns\b')
GOLD_MEMBER = re.compile(r'\bns\s*\.\s*Gold\s*\.\s*([A-Za-z_]\w*)')
SYMBOL_MEMBER = re.compile(r'\bns\s*\.\s*STEP_SYMBOLS\s*\.\s*([A-Za-z_]\w*)')
API_BINDING = re.compile(r'^\s*local\s+ns\s*=\s*_G\.WowTogetherModuleAPI\s*$')
GLOBAL_ESCAPE = re.compile(r'\b(?:_G|_ENV|getglobal|getfenv|setfenv|rawget|rawset|WowTogetherDB|WowTogetherCharDB|WowTogetherSharedNamespace)\b')


def violations(source):
    problems = []
    # Preserve line numbers while allowing access expressions to span lines.
    lines = [line.split('--', 1)[0] for line in source.splitlines()]
    code = '\n'.join(lines)
    line_number = lambda offset: code.count('\n', 0, offset) + 1
    for match in ACCESS.finditer(code):
        name = match.group(1) or match.group(3)
        if name not in ALLOWED:
            problems.append(f'{line_number(match.start())}: ns.{name} is outside the module API')
    for match in ALIAS.finditer(code):
        problems.append(f'{line_number(match.start())}: aliasing the core namespace is outside the module API')
    for number, line in enumerate(lines, 1):
        if API_BINDING.fullmatch(line):
            continue
        if GLOBAL_ESCAPE.search(line):
            problems.append(f'{number}: direct global access is outside the module API')
    literal_lookups = {match.start() for match in ACCESS.finditer(code) if match.group(3)}
    for match in DYNAMIC.finditer(code):
        if match.start() not in literal_lookups:
            problems.append(f'{line_number(match.start())}: dynamic namespace lookup is outside the module API')
    for match in GOLD_MEMBER.finditer(code):
        if match.group(1) not in {'Price', 'Suggestions', 'SessionCard'}:
            problems.append(f'{line_number(match.start())}: ns.Gold.{match.group(1)} is not an exported result')
    for match in SYMBOL_MEMBER.finditer(code):
        if match.group(1) != 'farm':
            problems.append(f'{line_number(match.start())}: only ns.STEP_SYMBOLS.farm is public')
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    folder = args.root / 'WowTogether_Gold'
    if not folder.exists():
        print('Gold module absent; boundary ready')
        return 0
    errors = []
    for path in sorted(folder.rglob('*.lua')):
        errors.extend(f'{path.relative_to(args.root)}:{error}'
                      for error in violations(path.read_text()))
    if errors:
        print('\n'.join(errors))
        return 1
    print('Gold module boundary passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
