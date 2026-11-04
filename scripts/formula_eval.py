"""Small, safe formula evaluator for the benchmark's deterministic Excel checks.

Supports literals, same-sheet A1 references/ranges, + - * / ^ %, comparisons,
SUM, COUNT, COUNTA, ABS, MIN, MAX, IF, IFERROR. Rejects external links,
unknown functions, circular formulas, unsupported Excel syntax. No Python eval.
Use as verification fallback when xlsx formula caches are missing.
"""
import math
import re
from openpyxl.formula import Tokenizer
from openpyxl.utils.cell import range_boundaries

PRECEDENCE = {'=': 1, '<>': 1, '<': 1, '>': 1, '<=': 1, '>=': 1,
              '+': 2, '-': 2, '*': 3, '/': 3, '^': 5}

class FormulaError(ValueError):
    pass

class Parser:
    def __init__(self, formula):
        self.tokens = list(Tokenizer(formula).items)
        self.index = 0
        if len(self.tokens) > 400:
            raise FormulaError('formula too complex')

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def pop(self):
        tok = self.peek()
        if tok is None:
            raise FormulaError('unexpected end of formula')
        self.index += 1
        return tok

    def parse(self):
        result = self.expr(0)
        if self.peek() is not None:
            raise FormulaError('unexpected token')
        return result

    def expr(self, min_prec):
        tok = self.pop()
        if tok.type == 'OPERATOR-PREFIX' and tok.value in ('+', '-'):
            lhs = ('unary', tok.value, self.expr(4))
        elif tok.type == 'PAREN' and tok.subtype == 'OPEN':
            lhs = self.expr(0)
            end = self.pop()
            if end.type != 'PAREN' or end.subtype != 'CLOSE':
                raise FormulaError('unmatched parenthesis')
        elif tok.type == 'FUNC' and tok.subtype == 'OPEN':
            name = tok.value[:-1].upper()
            args = []
            while True:
                cur = self.peek()
                if cur is None:
                    raise FormulaError('unclosed function')
                if cur.type == 'FUNC' and cur.subtype == 'CLOSE':
                    self.pop(); break
                args.append(self.expr(0))
                cur = self.peek()
                if cur and cur.type == 'SEP' and cur.subtype == 'ARG':
                    self.pop(); continue
                if cur and cur.type == 'FUNC' and cur.subtype == 'CLOSE':
                    self.pop(); break
                raise FormulaError('malformed function')
            lhs = ('func', name, args)
        elif tok.type == 'OPERAND':
            if tok.subtype == 'NUMBER':
                lhs = ('lit', float(tok.value))
            elif tok.subtype == 'TEXT':
                lhs = ('lit', tok.value[1:-1].replace('""','"'))
            elif tok.subtype == 'LOGICAL':
                lhs = ('lit', tok.value.upper() == 'TRUE')
            elif tok.subtype == 'RANGE':
                lhs = ('ref', tok.value)
            else:
                raise FormulaError('unsupported literal')
        else:
            raise FormulaError('unsupported expression start')
        while True:
            nxt = self.peek()
            if nxt is None:
                break
            if nxt.type == 'OPERATOR-POSTFIX' and nxt.value == '%':
                self.pop(); lhs = ('percent', lhs); continue
            if nxt.type != 'OPERATOR-INFIX' or nxt.value not in PRECEDENCE:
                break
            p = PRECEDENCE[nxt.value]
            if p < min_prec:
                break
            self.pop()
            rhs = self.expr(p if nxt.value == '^' else p+1)
            lhs = ('binary', nxt.value, lhs, rhs)
        return lhs

class SpreadsheetFormulaEvaluator:
    def __init__(self, formula_ws, cached_ws=None):
        self.ws = formula_ws
        self.cached = cached_ws
        self._visiting = set()
        self._memo = {}
        self._count = 0

    def cell(self, coordinate):
        coordinate = coordinate.replace('$','').upper()
        if not re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]{0,6}',coordinate):
            raise FormulaError('invalid cell reference')
        if coordinate in self._memo:
            return self._memo[coordinate]
        if coordinate in self._visiting:
            raise FormulaError('circular cell reference')
        self._count += 1
        if self._count > 20000:
            raise FormulaError('formula evaluation limit exceeded')
        self._visiting.add(coordinate)
        try:
            item = self.ws[coordinate]
            if item.data_type == 'f':
                result = self._value(Parser(item.value).parse())
                if self.cached is not None:
                    cached = self.cached[coordinate].value
                    if cached is not None:
                        if isinstance(cached, (int,float)) and isinstance(result, (int,float)):
                            if not math.isclose(cached, result, rel_tol=1e-9, abs_tol=1e-12):
                                raise FormulaError(f'formula/cache disagree at {coordinate}')
                        elif cached != result:
                            raise FormulaError(f'formula/cache disagree at {coordinate}')
            else:
                result = item.value
            self._memo[coordinate] = result
            return result
        finally:
            self._visiting.discard(coordinate)

    def _to_number(self, value):
        if value is None or value == '':
            return 0.0
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int,float)):
            return value
        raise FormulaError(f'non-numeric formula operand: {value!r}')

    def _flatten(self, items):
        for item in items:
            if isinstance(item,list):
                yield from self._flatten(item)
            else:
                yield item

    def _value(self, node):
        kind = node[0]
        if kind == 'lit': return node[1]
        if kind == 'ref':
            name = node[1]
            if '!' in name or '[' in name or ']' in name or '#' in name:
                raise FormulaError('external/sheet reference not supported')
            name = name.replace('$', '').upper()
            if ':' not in name:
                return self.cell(name)
            left, right = name.split(':',1)
            bounds = range_boundaries(f'{left}:{right}')
            x1,y1,x2,y2 = bounds
            if None in bounds or x2<x1 or y2<y1 or (x2-x1+1)*(y2-y1+1)>10000:
                raise FormulaError('invalid/oversized range')
            return [self.cell(self.ws.cell(r,c).coordinate)
                    for r in range(y1,y2+1) for c in range(x1,x2+1)]
        if kind == 'unary':
            x = self._to_number(self._value(node[2]));return x if node[1]=='+' else -x
        if kind == 'percent':return self._to_number(self._value(node[1]))/100
        if kind == 'binary':
            op = node[1]
            x = self._value(node[2]);y = self._value(node[3])
            if op in ('=', '<>', '<', '>', '<=', '>='):
                return {'=':lambda:x==y,'<>':lambda:x!=y,'<':lambda:x<y,'>':lambda:x>y,
                        '<=':lambda:x<=y,'>=':lambda:x>=y}[op]()
            x = self._to_number(x); y = self._to_number(y)
            if op=='+':return x+y
            if op=='-':return x-y
            if op=='*':return x*y
            if op=='/':return x/y
            if op=='^':return x**y
            raise FormulaError('unknown operator')
        if kind == 'func':
            name=node[1].upper()
            if name=='IF':
                if len(node[2]) not in (2,3):raise FormulaError('IF arguments')
                return self._value(node[2][1] if self._value(node[2][0]) else (node[2][2] if len(node[2])==3 else ('lit',False)))
            if name=='IFERROR':
                if len(node[2])!=2:raise FormulaError('IFERROR arguments')
                try:return self._value(node[2][0])
                except (FormulaError,ArithmeticError):return self._value(node[2][1])
            vals=list(self._flatten([self._value(arg) for arg in node[2]]))
            numeric=[v for v in vals if isinstance(v,(int,float)) and not isinstance(v,bool)]
            if name=='SUM':return sum(numeric)
            if name=='COUNT':return len(numeric)
            if name=='COUNTA':return sum(v is not None and v!='' for v in vals)
            if name=='ABS' and len(vals)==1:return abs(self._to_number(vals[0]))
            if name=='MIN' and numeric:return min(numeric)
            if name=='MAX' and numeric:return max(numeric)
            if name=='ROUND' and len(vals)==2:return round(self._to_number(vals[0]),int(vals[1]))
            raise FormulaError(f'unsupported function: {name}')
        raise FormulaError('unknown expression')
