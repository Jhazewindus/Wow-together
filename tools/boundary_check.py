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
TOKEN = re.compile(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|--\[\[.*?\]\]|--[^\n]*|\[\[.*?\]\]''', re.S)
ALIAS = re.compile(r'\b(?:local\s+)?([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\b')
GOLD_FIELDS = {'Price', 'Suggestions', 'SessionCard'}


def code_only(source):
    """Mask strings and comments while retaining offsets and line numbers."""
    return TOKEN.sub(lambda match: ''.join('\n' if c == '\n' else ' ' for c in match.group()), source)


def violations(source):
    code = code_only(source)
    problems = []
    aliases = {'ns'}
    changed = True
    while changed:
        changed = False
        for match in ALIAS.finditer(code):
            target, origin = match.groups()
            if origin in aliases and target not in aliases:
                aliases.add(target)
                changed = True
    for alias in aliases:
        access = re.compile(r'\b' + re.escape(alias) + r'\s*(?:\.\s*([A-Za-z_]\w*)|(\[))')
        for match in access.finditer(code):
            number = code.count('\n', 0, match.start()) + 1
            name = match.group(1)
            if not name:
                problems.append(f'{number}: dynamic namespace lookup is outside the module API')
                continue
            if name not in ALLOWED:
                problems.append(f'{number}: {alias}.{name} is outside the module API')
            if name in {'Gold', 'STEP_SYMBOLS'}:
                member = re.match(r'\s*(?:\.\s*([A-Za-z_]\w*)|(\[))', code[match.end():])
                if member:
                    field = member.group(1)
                    allowed = GOLD_FIELDS if name == 'Gold' else {'farm'}
                    if field not in allowed:
                        problems.append(f'{number}: {alias}.{name} member is outside the module API')
    for match in re.finditer(r'\b_G\s*\.\s*WowTogetherSharedNamespace\b', code):
        number = code.count('\n', 0, match.start()) + 1
        problems.append(f'{number}: raw core namespace handoff is forbidden')
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
