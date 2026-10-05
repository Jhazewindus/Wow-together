"""Parse literal-only public Lua data without evaluating source code."""
import math
import re

NUMBER = re.compile(r'-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?')
NAME = re.compile(r'[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*')


class LiteralParser:
    def __init__(self, text, symbols=None):
        self.text, self.pos, self.symbols = text, 0, symbols or {}

    def space(self):
        while self.pos < len(self.text):
            if self.text[self.pos].isspace(): self.pos += 1
            elif self.text.startswith('--', self.pos):
                end = self.text.find('\n', self.pos)
                self.pos = len(self.text) if end < 0 else end + 1
            else: break

    def consume(self, char):
        self.space()
        if not self.text.startswith(char, self.pos): raise ValueError('Expected literal token ' + char)
        self.pos += len(char)

    def string(self):
        quote = self.text[self.pos]; self.pos += 1; result = []
        while self.pos < len(self.text):
            char = self.text[self.pos]; self.pos += 1
            if char == quote: return ''.join(result)
            if char == '\\':
                if self.pos >= len(self.text): break
                char = self.text[self.pos]; self.pos += 1
                if char.isdigit():
                    digits = char
                    while len(digits) < 3 and self.pos < len(self.text) and self.text[self.pos].isdigit():
                        digits += self.text[self.pos]; self.pos += 1
                    value = int(digits)
                    if value > 255: raise ValueError('Invalid Lua string byte')
                    char = chr(value)
                else: char = {'n':'\n', 'r':'\r', 't':'\t', 'b':'\b', 'f':'\f', 'v':'\v', 'a':'\a'}.get(char, char)
            result.append(char)
        raise ValueError('Unterminated literal string')

    def value(self, depth=0):
        if depth > 48: raise ValueError('Literal nesting limit exceeded')
        self.space()
        if self.pos >= len(self.text): raise ValueError('Missing literal value')
        char = self.text[self.pos]
        if char in ('"', "'"): return self.string()
        if char == '{':
            self.pos += 1; result = {}; index = 1
            while True:
                self.space()
                if self.pos >= len(self.text): raise ValueError('Unterminated literal table')
                if self.text[self.pos] == '}': self.pos += 1; return result
                if self.text[self.pos] == '[':
                    self.pos += 1; key = self.value(depth+1); self.consume(']'); self.consume('=')
                else: key = index; index += 1
                if type(key) not in (str, int, float) or key in result: raise ValueError('Invalid/duplicate literal key')
                result[key] = self.value(depth+1)
                self.space()
                if self.pos < len(self.text) and self.text[self.pos] in ',;': self.pos += 1
                elif self.pos >= len(self.text) or self.text[self.pos] != '}': raise ValueError('Expected literal separator')
        number = NUMBER.match(self.text, self.pos)
        if number:
            self.pos += len(number[0]); result = float(number[0]) if any(c in number[0] for c in '.eE') else int(number[0])
            if not math.isfinite(result): raise ValueError('Nonfinite literal number')
            return result
        name = NAME.match(self.text, self.pos)
        if name:
            self.pos += len(name[0])
            if name[0] in ('nil', 'true', 'false'): return {'nil':None, 'true':True, 'false':False}[name[0]]
            if name[0] in self.symbols: return self.symbols[name[0]]
        raise ValueError('Source contains a non-literal expression')


def literal(text, symbols=None):
    parser = LiteralParser(text, symbols); result = parser.value(); parser.space()
    if parser.pos != len(text): raise ValueError('Unexpected content after literal')
    return result
