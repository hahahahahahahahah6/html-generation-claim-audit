"""Offline documentation and AST inspection; no source is executed."""
import ast
import os
from pathlib import Path
import re
from .phrases import HTMLGENERATION, NOHTMLGENERATION, GENERIC_NAMES


def normalize(text):
    return ' '.join(text.lower().replace('’', "'").replace("n't", ' not').replace('-', ' ').split())


def pattern(phrases):
    return re.compile(r'\b(?:' + '|'.join(re.escape(p) for p in sorted(phrases, key=lambda p: (-len(p), p))) + r')\b')


YES = pattern(HTMLGENERATION)
NO = pattern(NOHTMLGENERATION)


def match_paragraph(text):
    text = normalize(text)
    denial = bool(NO.search(text))
    return bool(YES.search(NO.sub(' ', text))), denial


def paragraphs(text):
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            lines.append('')
        elif marker:
            fence = marker[1]
            lines.append('')
        else:
            lines.append(line)
    return re.split(r'\n\s*\n', '\n'.join(lines))


def evidence(source):
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return False
    imports = {}
    shadows = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                imports[alias.asname or alias.name] = node.module + '.' + alias.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            shadows.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                shadows.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars:
                    shadows.update(n.id for n in ast.walk(item.optional_vars) if isinstance(n, ast.Name))
    def resolve(node):
        if isinstance(node, ast.Name):
            return imports.get(node.id, '') if node.id not in shadows else ''
        if isinstance(node, ast.Attribute):
            base = resolve(node.value)
            return base + '.' + node.attr if base else ''
        return ''
    flags = set()
    def literal(node):
        return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith(('.html', '.htm'))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        resolved = resolve(func)
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ''
        if name in shadows or (resolved and resolved.rsplit('.', 1)[-1] in shadows):
            continue
        if isinstance(func, ast.Attribute):
            if name in GENERIC_NAMES or name == 'to_html':
                return True
            if name in ('render', 'getvalue'):
                flags.add(name)
            if name == 'get_template' and node.args and literal(node.args[0]):
                flags.add('template')
        elif isinstance(func, ast.Name) and resolved and resolved.rsplit('.', 1)[-1] in GENERIC_NAMES:
            return True
        base = resolve(func.value) if isinstance(func, ast.Attribute) else ''
        if resolved in ('markdown.markdown', 'markdown.markdownFromFile', 'mammoth.convert_to_html'):
            return True
        if isinstance(func, ast.Attribute) and ((name in ('markdown', 'markdownFromFile') and (base == 'markdown' or base.startswith('markdown.'))) or (name == 'convert_to_html' and (base == 'mammoth' or base.startswith('mammoth.')))):
            return True
        if resolved == 'mako.template.Template' or (name == 'Template' and (base == 'mako' or base.startswith('mako.'))):
            if any(k.arg == 'filename' and literal(k.value) for k in node.keywords):
                flags.add('template')
        if resolved == 'dominate.document' or (name == 'document' and (base == 'dominate' or base.startswith('dominate.'))):
            flags.add('document')
        if resolved == 'yattag.Doc' or (name == 'Doc' and (base == 'yattag' or base.startswith('yattag.'))):
            flags.add('Doc')
    return ('render' in flags and bool(flags & {'template', 'document'})) or {'Doc', 'getvalue'} <= flags


def audit(root, ignore=(), fail_on='high'):
    root = Path(root)
    if not root.is_dir() or not os.access(root, os.R_OK | os.X_OK):
        raise OSError('Repository must be a readable directory: ' + str(root))
    claims, denials, production, tests = [], [], [], []
    prefixes = [p.replace('\\', '/').removeprefix('./').rstrip('/') for p in ignore]
    def ignored(path):
        return any(path.startswith(p) for p in prefixes)
    def walk_error(error):
        raise error
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(d for d in dirs if not (Path(directory)/d).is_symlink() and not ignored((Path(directory)/d).relative_to(root).as_posix()))
        for name in sorted(files):
            path = Path(directory)/name
            rel = path.relative_to(root)
            label = rel.as_posix()
            if path.is_symlink() or ignored(label):
                continue
            parts = rel.parts[:-1]
            if label == 'README.md' or (path.suffix == '.md' and 'docs' in parts):
                for paragraph in paragraphs(path.read_text(encoding='utf-8')):
                    yes, no = match_paragraph(paragraph)
                    if yes and label not in claims:
                        claims.append(label)
                    if no and label not in denials:
                        denials.append(label)
            if path.suffix != '.py' or any(p in parts for p in ('fixtures', 'docs', 'examples')):
                continue
            if evidence(path.read_text(encoding='utf-8')):
                is_test = 'tests' in parts or name.startswith('test_') or name.endswith('_test.py')
                (tests if is_test else production).append(label)
    findings = []
    if claims and not production:
        findings.append({'rule': 'documented-html-generation-claim-false', 'severity': 'MEDIUM' if tests else 'HIGH', 'message': 'The documented capability has evidence only in tests.' if tests else 'The documented capability has no listed production evidence.', 'locations': claims})
    if denials and production:
        findings.append({'rule': 'documented-no-html-generation-claim-false', 'severity': 'HIGH', 'message': 'A documented denial conflicts with listed production evidence.', 'locations': denials})
    failed = any(f['severity'] == 'HIGH' or fail_on == 'medium' for f in findings)
    return {'verdict': 'FAIL' if failed else 'PASS', 'findings': findings, 'production_evidence': production, 'test_evidence': tests, 'claims': claims, 'denials': denials}
