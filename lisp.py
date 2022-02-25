import builtins
import importlib
import operator as op
import re
from collections import ChainMap
from functools import reduce
from typing import Any, Iterator, NamedTuple, Union

re_tokens = re.compile(
    r"""
          \(
        | \)
        | [^"\(\)\s]+  # atom
        | "[^"]+"      # string
    """,
    re.VERBOSE,
)

re_true = re.compile(r"#t$")
re_false = re.compile(r"#f$")
re_int = re.compile(r"[-+]?(0[xX][\dA-Fa-f]+|0[0-7]*|\d+)$")
re_float = re.compile(r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$")
re_string = re.compile(r'"[^"]+"$')


class ParserError(Exception):
    pass


def tokenize(source: str) -> Iterator[str]:
    while True:
        source = source.lstrip()
        if not source:
            break

        if not (m := re_tokens.match(source)):
            raise ParserError("Invalid syntax")

        yield m.group(0)
        source = source[m.end():]


class Symbol(NamedTuple):
    name: str


Atom = int | float | str | bool | Symbol
Expr = Union[Atom, list[Any]]  # Recursive types not supported


def atom(token: str) -> Atom:
    patterns = {
        re_true: lambda _: True,
        re_false: lambda _: False,
        re_int: int,
        re_float: float,
        re_string: lambda s: s[1:-1],
    }
    for pattern, fn in patterns.items():
        if re.match(pattern, token):
            return fn(token)
    return Symbol(token)


def parse(source: str) -> list[Expr]:
    stack, current = [], []
    for token in tokenize(source):
        if token == "(":
            stack.append(current)
            current = []
        elif token == ")":
            if not stack:
                raise ParserError("Unmatched parenthesis")
            tmp, current = current, stack.pop()
            current.append(tmp)
        else:
            current.append(atom(token))
    if stack:
        raise ParserError("Unmatched parenthesis")
    return current


class EvalError(Exception):
    pass


class Lambda(NamedTuple):
    arg_names: list[str]
    code: list[Expr]
    env: dict[str, Any]

    def __call__(self, *args):
        assert len(args) == len(self.arg_names)
        params = dict(zip(self.arg_names, args))
        return eval_(self.code, ChainMap(params, self.env))


def eval_(exp: Expr, env: dict[str, Any]):
    special_forms = ("if", "define", "quote")
    match exp:
        case [Symbol("if"), cond, when_true, when_false]:
            return eval_(when_true if eval_(cond, env) else when_false, env)

        case [Symbol("define"), Symbol(name), value]:
            env[name] = eval_(value, env)

        case [Symbol("quote"), arg]:
            return arg

        case [Symbol("lambda"), [*arg_names], code]:
            return Lambda([arg.name for arg in arg_names], code, env)

        case Symbol(name) if name in special_forms and name not in env:
            raise EvalError(f"Bad syntax in {name}")

        case Symbol(name):
            try:
                return env[name]
            except KeyError:
                raise EvalError(f"Undefined symbol {name}")

        case [symbol, *args]:
            fn = eval_(symbol, env)
            return fn(*(eval_(arg, env) for arg in args))

        case _:
            return exp


def repr_(value) -> str:
    match value:
        case True:
            return "#t"
        case False:
            return "#f"
        case int() | float() | str():
            return repr(value)
        case list():
            return f"({' '.join(map(repr_, value))})"
        case Symbol(name):
            return name
        case Lambda(arg_names):
            return f"lambda:({' '.join(arg_names)})"
        case _:
            return f"py.{type(value).__qualname__}:{repr(value)}"


lisp_builtins = {
    "#import": importlib.import_module,
    "#py": lambda name: getattr(builtins, name),
    "+": lambda *args: sum(args),
    "-": lambda arg, *rest: reduce(op.sub, rest, arg) if rest else op.neg(arg),
    "*": lambda *args: reduce(op.mul, args, 1),
    "/": lambda *args: reduce(op.truediv, args, 1),
    ">": op.gt,
    "<": op.lt,
    "=": op.eq,
    "<=": op.le,
    ">=": op.ge,
    "print": print,
    "car": lambda x: x[0],
    "cdr": lambda x: x[1:],
    "list": lambda *args: list(args),
    "map": lambda f, args: list(map(f, args)),
    "varargs": lambda f: lambda *args: f(args),
}


if __name__ == "__main__":
    import readline
    import os

    history_file = os.path.expanduser("~/.lisppy_history")
    if os.path.exists(history_file):
        readline.read_history_file(history_file)

    def format_error(msg):
        return f"\033[91m{msg}\033[0m"

    env = {} | lisp_builtins
    while True:
        try:
            raw_input = input("> ")
            readline.write_history_file(history_file)
        except (EOFError, KeyboardInterrupt):
            break

        try:
            expressions = parse(raw_input)
        except ParserError as e:
            print(format_error(e))
            continue

        for exp in expressions:
            try:
                rv = eval_(exp, env)
            except EvalError as e:
                print(format_error(e))
            else:
                if rv is not None:
                    print(repr_(rv))
