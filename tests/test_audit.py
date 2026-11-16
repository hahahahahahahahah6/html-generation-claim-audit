import unittest
from html_generation_claim_audit import phrases
from html_generation_claim_audit.audit import evidence, audit, match_paragraph

class AuditTests(unittest.TestCase):
    def test_phrase_oracle(self):
        self.assertEqual(phrases.HTMLGENERATION, ('html generation', 'generate html', 'generates html', 'generating html', 'create html', 'creates html', 'creating html', 'export html', 'exports html', 'exporting html', 'export to html', 'exports to html', 'exporting to html', 'export as html', 'exports as html', 'exporting as html', 'html export', 'html exports', 'html exporter', 'html page generation', 'generate html page', 'generates html page', 'generating html page', 'generate html pages', 'create html page', 'creates html page', 'write html', 'writes html', 'writing html', 'save as html', 'saves as html', 'save to html', 'saves to html', 'html writer', 'html writing', 'build html', 'builds html', 'building html', 'render html', 'renders html', 'rendering html', 'generate html document', 'generates html document', 'create html document', 'creates html document', 'html document generation', 'generate web page', 'generates web page', 'web page generation', 'webpage generation'))
        self.assertEqual(phrases.NOHTMLGENERATION, ('no html generation', 'does not generate html', 'does not support html generation', 'without html generation', 'no html export', 'does not export html', 'does not export to html', 'does not create html', 'no html writer', 'does not write html', 'does not save as html', 'no html page generation', 'does not generate html pages', 'does not build html', 'does not generate html page', 'does not create html page', 'html generation not supported', 'no html generation support', 'without html export', 'does not support html export', 'no html exporter', 'does not generate web page', 'no webpage generation', 'does not render html'))
        self.assertEqual(phrases.GENERIC_NAMES, ('generate_html', 'create_html', 'export_html', 'export_to_html', 'export_as_html', 'write_html', 'save_html', 'save_as_html', 'build_html', 'render_html', 'make_html', 'generate_html_page', 'create_html_page', 'export_html_page', 'write_html_page', 'generate_webpage', 'create_webpage', 'export_webpage', 'generate_html_document', 'create_html_document', 'export_html_document', 'write_html_document', 'render_html_page', 'generate_html_pages'))

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from html_generation_claim_audit.__main__ import main

GOOD = [
 'env.get_template("x.html").render()', 'env.get_template("x.htm"); t.render()',
 'from mako.template import Template\nt=Template(filename="x.html"); t.render()',
 'lookup.get_template("x.html"); t.render()',
 'import dominate as d\nx=d.document(); x.render()',
 'from dominate import document as D\nx=D(); x.render()',
 'import yattag as y\nx=y.Doc(); x.getvalue()',
 'from yattag import Doc as D\nx=D(); x.getvalue()',
 'import markdown as m\nm.markdown("x")', 'import markdown\nmarkdown.markdownFromFile(input="x")',
 'from markdown import markdown as m\nm("x")',
 'from markdown import markdownFromFile as m\nm(input="x")',
 'import mammoth as m\nm.convert_to_html(x)',
 'from mammoth import convert_to_html as c\nc(x)', 'df.to_html()',
 'import mako.template as m\nt=m.Template(filename="x.htm"); t.render()',
 'import mako\nt=mako.template.Template(filename="x.html"); t.render()',
 'from somewhere import generate_html as g\ng()',
]
BAD = [
 'import jinja2', 'from jinja2 import Template\nTemplate("x").render()',
 'env.get_template("report.txt"); t.render()',
 'from string import Template\nTemplate("x").substitute()',
 'from mako.template import Template\nTemplate(text="x").render()',
 'from mako.template import Template\nTemplate(filename="x.txt").render()',
 'from mako.template import Template\nTemplate(filename="x.html")',
 'import jinja2\njinja2.Environment()', 'import dominate\ndominate.document()',
 'import yattag\nyattag.Doc()', 'import mammoth\nmammoth.convert_to_markdown(x)',
 'import docx2txt\ndocx2txt.process(x)', 'soup.prettify()', 'str(soup)', 'lxml.tostring(tree)',
 'x._repr_html_()', 'flask.render_template("x.html")', 'django.render(x)', 'HttpResponse("<html>")',
 'from weasyprint import HTML\nHTML("x").write_pdf("x.pdf")',
 'Canvas("x.pdf").save()', 'FPDF().output("x.pdf")', 'pypdf.PdfWriter().write(x)',
 'fitz.open().save("x.pdf")', 'openpyxl.Workbook().save("x.xlsx")',
 'xlsxwriter.Workbook("x.xlsx").close()', 'pandas.DataFrame().to_excel("x.xlsx")',
 'docx.Document().save("x.docx")', 'pptx.Presentation().save("x.pptx")',
 'open("x.html", "w").write("<html>")', 'Path("x.html").write_text("<html>")',
 'html.parser.HTMLParser().feed("<html>")', 'html5lib.parse("<html>")',
 'subprocess.run(["pandoc", "-o", "x.html"])', 'subprocess.run(["wkhtmltopdf", "x.html"])',
 '"html"', '"web page"', '# generate html\n"generate html"', 'x.generate_html', 'generate_html()',
 'def broken(:', 'client.parse(InvoiceV4, x)', 'client.begin_analyze_document("prebuilt-layout", x)',
 'veryfi.Client().process_document(x)', 'documentai.process_document(x)', 'textract.analyze_document(x)',
 'eden.universal_ai(model_id="x")', 'LlamaParse().load_data(x)', 'nanonets.OCR(model_id="opaque")',
 'docsumo.upload(x)', 'abbyy.process(skill="opaque")', 'rossum.upload(queue="opaque")',
 'klippa.parse(x)', 'parseur.upload(x)', 'extend.process(workflow="opaque")',
 'def generate_html(): pass\nx.generate_html()',
 'class C:\n def generate_html(self): pass\nx.generate_html()',
 'from markdown import markdown\nmarkdown = other\nmarkdown("x")',
 'import markdown as m\nm: object = other\nm.markdown("x")',
 'import mammoth as m\nwith ctx as m:\n m.convert_to_html(x)',
 'from yattag import Doc\nclass Doc: pass\nDoc().getvalue()',
 'from mako.template import Template\ndef Template(): pass\nTemplate(filename="x.html").render()',
]

def add_evidence_test(index, source, expected):
    def check(self):
        self.assertEqual(evidence(source), expected, source)
    setattr(AuditTests, 'test_evidence_%s_%03d' % ('yes' if expected else 'no', index), check)

for i, source in enumerate(GOOD):
    add_evidence_test(i, source, True)
for i, source in enumerate(BAD):
    add_evidence_test(i, source, False)
for i, name in enumerate(phrases.GENERIC_NAMES):
    add_evidence_test(100+i, 'x.'+name+'()', True)
    add_evidence_test(200+i, 'from lib import '+name+' as f\nf()', True)
    add_evidence_test(100+i, 'def '+name+'(): pass\nx.'+name+'()', False)

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        # All transient fixtures stay inside the requested output tree.
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
    def put(self, name, text):
        p = self.root/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    def run_cli(self, *args):
        p = subprocess.run([sys.executable, '-m', 'html_generation_claim_audit', *args], text=True, capture_output=True)
        return p
    def test_good(self):
        self.put('README.md', 'generate html'); self.put('app.py', 'x.to_html()')
        self.assertEqual(audit(self.root)['verdict'], 'PASS')
    def test_bad(self):
        self.put('README.md', 'generate html'); self.put('app.py', 'pass')
        p=self.run_cli('audit', str(self.root), '--json')
        self.assertEqual(p.returncode,2)
        r=json.loads(p.stdout); self.assertEqual(r['verdict'],'FAIL')
        self.assertEqual([(x['rule'],x['severity']) for x in r['findings']], [('documented-html-generation-claim-false','HIGH')])
        self.assertTrue(r['findings'][0]['message'])
    def test_test_only(self):
        self.put('README.md', 'generate html'); self.put('tests/e.py','x.to_html()')
        self.assertEqual(audit(self.root)['findings'][0]['severity'],'MEDIUM')
        self.assertEqual(self.run_cli('audit',str(self.root)).returncode,0)
        self.assertEqual(self.run_cli('audit',str(self.root),'--fail-on','medium').returncode,2)
    def test_denial(self):
        self.put('README.md','does not generate html'); self.put('a.py','x.to_html()')
        r=audit(self.root)
        self.assertEqual([(x['rule'],x['severity']) for x in r['findings']],[('documented-no-html-generation-claim-false','HIGH')])
        self.assertEqual(self.run_cli('audit',str(self.root)).returncode,2)
    def test_no_source(self):
        self.put('README.md','generate html'); self.assertEqual(audit(self.root)['verdict'],'FAIL')
        self.put('README.md','does not generate html'); self.assertEqual(audit(self.root)['verdict'],'PASS')
    def test_no_claim(self):
        self.put('README.md','A tool'); self.assertEqual(audit(self.root)['verdict'],'PASS')
    def test_fences(self):
        for fence in ['```','~~~','   ````']:
            self.put('README.md',fence+'\ngenerate html\n'+fence)
            self.assertEqual(audit(self.root)['verdict'],'PASS')
        self.put('README.md','`generate html`'); self.assertEqual(audit(self.root)['verdict'],'FAIL')
    def test_all_phrases(self):
        for p in phrases.HTMLGENERATION: self.assertEqual(match_paragraph(p),(True,False),p)
        for p in phrases.NOHTMLGENERATION: self.assertEqual(match_paragraph(p),(False,True),p)
        self.assertEqual(match_paragraph("doesn't generate-html"),(False,True))
        self.assertEqual(match_paragraph('regenerate htmlish'),(False,False))
    def test_split_modules(self):
        for first,last in [('e.get_template("x.html")','t.render()'),('import dominate\ndominate.document()','t.render()'),('import yattag\nyattag.Doc()','t.getvalue()'),('from mako.template import Template\nTemplate(filename="x.html")','t.render()')]:
            self.put('README.md','generate html'); self.put('a.py',first); self.put('b.py',last)
            self.assertEqual(audit(self.root)['verdict'],'FAIL')
    def test_exclusions(self):
        self.put('README.md','generate html')
        for name in ['fixtures/a.py','docs/a.py','examples/a.py']:
            self.put(name,'x.to_html()')
        self.assertEqual(audit(self.root)['findings'][0]['severity'],'HIGH')
        for name in ['tests/a.py','test_a.py','a_test.py']:
            self.put(name,'x.to_html()')
        self.assertEqual(audit(self.root)['findings'][0]['severity'],'MEDIUM')
    def test_symlinks(self):
        self.put('README.md','generate html'); self.put('fixtures/real.py','x.to_html()')
        (self.root/'link.py').symlink_to(self.root/'fixtures/real.py')
        (self.root/'linked').symlink_to(self.root/'fixtures',target_is_directory=True)
        self.assertEqual(audit(self.root)['verdict'],'FAIL')
    def test_docs_and_ignore(self):
        self.put('nested/docs/topic.md','generate html'); self.put('other.md','does not generate html')
        self.put('src/a.py','x.to_html()')
        self.assertEqual(audit(self.root)['verdict'],'PASS')
        self.assertEqual(audit(self.root, ['src'])['verdict'],'FAIL')
        self.assertEqual(audit(self.root, ['nested','src'])['verdict'],'PASS')
    def test_errors(self):
        for args in [[],['bogus'],['audit','/nonexistent'],['audit',str(self.root),'--fail-on','MEDIUM'],['audit','--ignore']]:
            self.assertEqual(self.run_cli(*args).returncode,1,args)
    def test_version(self):
        p=self.run_cli('--version'); self.assertEqual((p.returncode,p.stdout.strip()),(0,'0.1.0'))
    def test_verbose(self):
        self.assertIn('production_evidence',self.run_cli('audit',str(self.root),'--verbose').stdout)

if __name__ == '__main__':
    unittest.main()
