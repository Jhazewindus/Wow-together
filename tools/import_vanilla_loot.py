"""Read literal Vanilla database rows, never evaluate JavaScript."""
import re


class LiteralReader:
    def __init__(self, text):
        self.text, self.position = text, 0

    def space(self):
        while self.position < len(self.text) and self.text[self.position].isspace():
            self.position += 1

    def string(self):
        quote = self.text[self.position]
        self.position += 1
        result = []
        while self.position < len(self.text):
            value = self.text[self.position]
            self.position += 1
            if value == quote:
                return ''.join(result)
            if value == '\\':
                value = self.text[self.position]
                self.position += 1
                if value in ('u', 'x'):
                    count = 4 if value == 'u' else 2
                    digits = self.text[self.position:self.position + count]
                    if not re.fullmatch('[0-9a-fA-F]{' + str(count) + '}', digits):
                        raise ValueError('Invalid literal escape')
                    value = chr(int(digits, 16))
                    self.position += count
                else:
                    value = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f'}.get(value, value)
            result.append(value)
        raise ValueError('Unterminated literal string')

    def value(self):
        self.space()
        char = self.text[self.position]
        if char in ('"', "'"):
            return self.string()
        if char in ('[', '{'):
            array = char == '['
            self.position += 1
            result = [] if array else {}
            end = ']' if array else '}'
            while True:
                self.space()
                if self.text[self.position] == end:
                    self.position += 1
                    return result
                if array:
                    result.append(self.value())
                else:
                    if self.text[self.position] in ('"', "'"):
                        key = self.string()
                    else:
                        match = re.match(r'[A-Za-z_$][\w$]*|\d+', self.text[self.position:])
                        if not match:
                            raise ValueError('Invalid literal property')
                        key = match.group()
                        self.position += len(key)
                    self.space()
                    if self.text[self.position] != ':':
                        raise ValueError('Expected literal colon')
                    self.position += 1
                    result[key] = self.value()
                self.space()
                char = self.text[self.position]
                if char == ',':
                    self.position += 1
                elif char != end:
                    raise ValueError('Nonliteral expression rejected')
        match = re.match(r'-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', self.text[self.position:])
        if match:
            self.position += len(match.group())
            return float(match.group()) if any(v in match.group() for v in '.eE') else int(match.group())
        for token, value in [('true', True), ('false', False), ('null', None)]:
            if self.text.startswith(token, self.position):
                self.position += len(token)
                return value
        raise ValueError('Nonliteral value rejected')


def vanilla_rows(page, name='drop'):
    marker = re.search(r"new Listview\(\{\s*template\s*:\s*['\"]item['\"],\s*id\s*:\s*['\"]" + re.escape(name) + "['\"]", page)
    if not marker:
        return []
    data = re.search(r'\bdata\s*:', page[marker.end():])
    if not data:
        raise ValueError('Missing literal data')
    rows = LiteralReader(page[marker.end() + data.end():]).value()
    if not isinstance(rows, list):
        raise ValueError('Expected literal drop array')
    for row in rows:
        name = row.get('name', '')
        if not re.match(r'^[0-7]', name):
            raise ValueError('Unrecognized item quality encoding')
        row['quality'], row['name'] = 7 - int(name[0]), name[1:]
    return rows
