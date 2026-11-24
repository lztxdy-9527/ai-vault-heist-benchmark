"""Private JSON worker for Half 2 (v2.2). No engine, map, or other contestant is imported here.

The language guard enforces the contest API, not an OS security boundary.
Run genuinely hostile submissions in an OS sandbox with resource limits.
"""
import ast
import builtins
import importlib
import json
import random
import string
import sys
import types

ALLOWED_TOP_MODULES = set((
    'abc array base64 binascii bisect calendar cmath collections contextlib '
    'copy dataclasses datetime decimal difflib enum fractions functools '
    'graphlib hashlib heapq hmac itertools json keyword math numbers operator '
    'pprint queue random re reprlib secrets statistics string stringprep '
    'struct textwrap time typing unicodedata weakref zlib '
    'numpy networkx sympy mpmath typing_extensions'
).split())
BLOCKED_SUBMODULES = {'ctypeslib', 'f2py', 'testing', 'distutils', 'readwrite', 'npyio'}
BLOCKED = set('open input eval exec compile globals locals vars getattr setattr delattr breakpoint help dir memoryview'.split())
BLOCKED_ATTRS = {
    'gi_frame', 'gi_code', 'cr_frame', 'cr_code', 'ag_frame', 'ag_code',
    'tb_frame', 'f_globals', 'f_builtins', 'f_locals', 'f_back', 'f_code',
    '_getframe', '_current_frames', '_current_exceptions', '_module',
    'tofile', 'fromfile', 'loadtxt', 'genfromtxt', 'memmap',
    'savetxt', 'savez', 'savez_compressed',
}
BLOCKED_MODULE_ATTRS = {
    'attrgetter', 'methodcaller', 'get_type_hints', 'ForwardRef',
    'singledispatch', 'singledispatchmethod',
    'sys', 'os', 'builtins', 'io', 'open', 'ctypes', 'subprocess',
    'pickle', 'marshal', 'shelve', 'codecs', 'importlib', 'inspect',
    'load', 'save', 'loadtxt', 'savetxt', 'savez', 'savez_compressed',
    'fromfile', 'genfromtxt', 'memmap', 'ctypeslib', 'f2py', 'testing', 'readwrite',
}
ALLOWED_INTERNAL_IMPORTS = {'numpy._core._methods', '_strptime'}


def is_allowed_module(name):
    if not name:
        return False
    parts = name.split('.')
    if parts[0] not in ALLOWED_TOP_MODULES:
        return False
    return all(p and not p.startswith('_') and p not in BLOCKED_SUBMODULES for p in parts)


def is_blocked_module_attr(name):
    return name.startswith('_') or name in BLOCKED_MODULE_ATTRS or name.startswith(('read_', 'write_'))


def checked_attribute(obj, name):
    if name.startswith('__') or name in BLOCKED_ATTRS:
        raise ValueError('Forbidden attribute access')
    if isinstance(obj, (types.ModuleType, ModuleView)) and is_blocked_module_attr(name):
        raise ValueError('Forbidden module attribute access')
    value = getattr(obj, name)
    if name not in {'format', 'format_map'} or not (isinstance(obj, str) or obj is str):
        return value

    def checked_format(*args, **kwargs):
        template = obj if isinstance(obj, str) else args[0]

        def check(text):
            for _, field, spec, _ in string.Formatter().parse(text):
                if field is not None and '.' in field:
                    raise ValueError('Attribute traversal in format strings denied')
                if spec:
                    check(spec)

        check(template)
        return value(*args, **kwargs)

    return checked_format


class AttributeGuard(ast.NodeTransformer):
    def visit_Attribute(self, node):
        self.generic_visit(node)
        if isinstance(node.ctx, ast.Load):
            return ast.copy_location(
                ast.Call(
                    func=ast.Name(id='_checked_attribute', ctx=ast.Load()),
                    args=[node.value, ast.Constant(node.attr)],
                    keywords=[],
                ),
                node,
            )
        return node


class ModuleView:
    def __init__(self, module):
        self._module = module

    def __getattr__(self, name):
        if is_blocked_module_attr(name):
            raise ImportError('Private, reflective, or I/O module access denied')
        value = getattr(self._module, name)
        if isinstance(value, types.ModuleType):
            if not is_allowed_module(value.__name__):
                raise ImportError('Module dependency access denied')
            return ModuleView(value)
        return value


def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if not level and not fromlist and name in ALLOWED_INTERNAL_IMPORTS:
        return ModuleView(importlib.import_module(name))
    if level or not is_allowed_module(name):
        raise ImportError('Module is not allowed')
    if fromlist:
        if any(is_blocked_module_attr(item) for item in fromlist):
            raise ImportError('Forbidden import target')
        return ModuleView(importlib.import_module(name))
    importlib.import_module(name)
    return ModuleView(importlib.import_module(name.split('.')[0]))


def load_source(source):
    tree = ast.parse(source, filename='<submission>')
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and (node.attr.startswith('__') or node.attr in BLOCKED_ATTRS):
            raise ValueError('Forbidden attribute access')
        if isinstance(node, ast.Name) and (node.id in BLOCKED or node.id.startswith('__')):
            raise ValueError('Reflective or I/O builtin denied')
        if isinstance(node, ast.Import):
            if any(not is_allowed_module(a.name) for a in node.names):
                raise ImportError('Module is not allowed')
        if isinstance(node, ast.ImportFrom):
            if (node.level or not node.module or not is_allowed_module(node.module)
                    or any(a.name == '*' or is_blocked_module_attr(a.name) for a in node.names)):
                raise ImportError('Module import target is not allowed')
    names = set(('abs all any ascii bin bool bytearray bytes callable chr classmethod complex '
                 'dict divmod enumerate filter float format frozenset hash hex id int isinstance '
                 'issubclass iter len list map max min next oct ord pow print property range repr '
                 'reversed round set slice sorted staticmethod str sum tuple type zip '
                 'Exception ValueError TypeError KeyError IndexError RuntimeError StopIteration '
                 'NotImplementedError ArithmeticError ZeroDivisionError AssertionError __build_class__').split())
    safe = {k: getattr(builtins, k) for k in names}
    safe['__import__'] = guarded_import
    safe['print'] = lambda *a, **kw: None
    namespace = {'__builtins__': safe, '__name__': 'submission', '_checked_attribute': checked_attribute}
    random.seed(20261115)
    tree = ast.fix_missing_locations(AttributeGuard().visit(tree))
    exec(compile(tree, '<submission>', 'exec'), namespace)
    return namespace


def reply(value):
    raw = json.dumps(value, ensure_ascii=True, allow_nan=False)
    if len(raw) > 2_000_000:
        raise ValueError('Reply too large')
    sys.stdout.write(raw + '\n')
    sys.stdout.flush()


def main():
    reply({'ok': True, 'ready': True})
    namespace, memory = {}, {}
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request['op'] == 'load':
                namespace = load_source(request['source'])
                result = True
            elif request['op'] == 'build':
                result = namespace['build_dungeon']()
            elif request['op'] == 'decide':
                result = namespace['decide_action'](request['state'], memory)
                if not isinstance(result, str):
                    raise ValueError('Action must be a string')
            else:
                raise ValueError('Unknown operation')
            reply({'ok': True, 'result': result})
        except BaseException as error:
            reply({'ok': False, 'error': type(error).__name__})


if __name__ == '__main__':
    main()
