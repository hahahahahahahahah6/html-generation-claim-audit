# Documentation claim auditor

A standard-library-only, offline static auditor comparing documented claims
with listed Python AST fingerprints. It never executes the inspected source,
uses the network, or changes the inspected repository. Requires Python 3.9 or later.

Install a local distribution and run either entry point:

```sh
python3 -m pip install --no-index dist/html_generation_claim_audit-0.1.0-py3-none-any.whl
html-generation-claim-audit --version
html-generation-claim-audit audit /path/to/repository --json
python3 -m html_generation_claim_audit audit /path/to/repository --verbose
python3 -m html_generation_claim_audit audit . --ignore build --ignore dist --fail-on medium
python3 -m unittest discover
```

The repository argument defaults to the current directory. Repeated ignore
arguments exclude path prefixes. The failure threshold accepts lowercase high
(default) or medium. Exit status is 0 for PASS, 2 for findings at or above the
threshold, and 1 for usage or I/O errors. A medium finding remains visible even
when the default threshold permits PASS. Version output is 0.1.0.

JSON contains verdict, findings, production_evidence, test_evidence, claims and
denials. Each finding includes rule, severity, message and locations. Text output
shows the verdict and findings; verbose mode adds the full structured result.

```text
documented-html-generation-claim-false HIGH
  Positive claim without listed production evidence.
documented-html-generation-claim-false MEDIUM
  Positive claim supported only by test evidence.
documented-no-html-generation-claim-false HIGH
  Denial conflicts with production evidence.
```

Only the root README.md and Markdown files beneath any docs path component
supply claims. Backtick and tilde fences with up to three leading spaces are
excluded; inline code counts. Paragraphs split at blank lines. Matching lowercases,
expands negative contractions, replaces hyphens with spaces, collapses whitespace,
and uses exact word boundaries, longest phrases first with alphabetical ties.
Denial spans are removed before positive matching. There is at most one finding
per claim family. A positive claim without source files fails; a denial without
source files passes.

Python files are parsed with AST and never executed. Symlinked files and
directories are skipped. Files beneath fixtures, docs or examples supply no
evidence. Files beneath tests, or named test_*.py or *_test.py, count separately
as test evidence. Invalid syntax supplies no evidence. Paired operations must
appear in the same module; receiver identity and control flow are not proved.
Imports and aliases are resolved; local function, method, class, assignment,
annotated assignment and context-manager bindings shadow imported names.

The supported library fingerprints are:

```text
jinja2: get_template("x.html" or "x.htm") + .render()
Mako: imported mako.template.Template(filename="x.html" or "x.htm") + .render()
      or get_template("x.html" or "x.htm") + .render()
dominate: imported document construction + .render()
yattag: imported Doc construction + .getvalue()
markdown: imported markdown(...) or markdownFromFile(...)
mammoth: imported convert_to_html(...)
pandas: any .to_html(...) call
```

The template lookup pattern is deliberately receiver-agnostic: a Django loader
lookup with the listed extension plus a render call also qualifies. Generic
attribute calls qualify on any base, while generic bare-name calls require a
resolvable from-import. Locally defined route names are excluded. The complete
vocabulary is available in the installed source:

```text
html_generation_claim_audit/phrases.py
```

Static matching is not semantic judgement: dead code counts, unsupported alias
chains are missed, wording outside the exact lists is missed, and denial
handling depends on the denial list. Adjacent document formats, field extraction,
image synthesis and text synthesis are outside the checked claim family.

Some documented wording has ambiguous meanings. An empty file shell, a download
menu for existing output, server-side page delivery, a document delivered in a
browser format, a GUI save option, a reader-wrapper class or job title, an assembly
build step and browser display can all trigger a claim without a supported
fingerprint. Only source evidence resolves these cases. Examples of the checked
wording, shown as data rather than claims about this auditor:

```text
html generation; generate html; create html; export html
web page generation; webpage generation; generate web page
html document generation; generate html document
save as html; save to html; html writer; html writing
build html; building html; render html; rendering html
```

These operations do not qualify; the reasons are part of the detector's limits:

```text
jinja2 Template.render alone: no .html/.htm lookup fingerprint.
jinja2 get_template("report.txt"): extension supplies no proof.
Mako Template(text=...): no filename proof; .txt filenames also excluded.
Lone Environment, Template, dominate document or yattag Doc constructions:
  no paired render/getvalue operation.
Bare imports, strings, comments, name references: no qualifying call.
open("x.html", "w").write(...) / Path.write_text(...): hand-written strings
  are not detected; the detector requires a listed call.
BeautifulSoup prettify / str(soup) / lxml tostring: parsed-content reserialization.
_repr_html_: notebook display hook.
Flask render_template / Django render / HttpResponse alone: response rendering.
WeasyPrint HTML + write_pdf; reportlab / fpdf / pypdf / PyMuPDF: PDF output.
openpyxl / xlsxwriter / pandas to_excel: spreadsheet output.
python-docx Document + save: Word output.
python-pptx Presentation + save: presentation output.
mammoth convert_to_markdown / docx2txt.process: Markdown or raw-text output.
html5lib / html.parser: parsing.
pandoc / wkhtmltopdf / any subprocess CLI: external binaries are excluded.
Mindee parse with any product; Azure begin_analyze_document or
  begin_analyze_document_from_url with any model; Veryfi with any method;
  Google Document AI process_document / batch_process_documents with any processor;
  Eden AI universal-ai with any model; Textract; LlamaParse:
  document reading/extraction, without a listed output fingerprint.
Nanonets / Docsumo / ABBYY Vantage / Rossum / Klippa / Parseur / Extend:
  opaque IDs or externally configured upload endpoints; extraction-side only.
```

Builds use local cached tools without package-index access:

```sh
PIP_NO_INDEX=1 PYTHONPATH=/path/to/extracted/build/tools python3 -m build --no-isolation --skip-dependency-check
```

MIT licensed. No runtime dependencies.
