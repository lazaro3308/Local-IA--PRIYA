import tempfile
import unittest
from pathlib import Path

from docx import Document
import pymupdf

from pria.tools.documents import DocumentTools
from pria.tools.files import FileToolError, FileTools


class DocumentToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.tools = DocumentTools()

    def tearDown(self):
        self.temp.cleanup()

    def test_pdf_extraction_includes_page_citations(self):
        path = self.root / "relatorio.pdf"
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((72, 72), "Conteudo de teste da pagina um", fontname="helv")
            pdf.save(path)
        result = FileTools().read_document(path)
        self.assertIn("[Página 1]", result)
        self.assertIn("Conteudo de teste da pagina um", result)

    def test_docx_extraction_includes_paragraphs_and_tables(self):
        path = self.root / "nota.docx"
        doc = Document()
        doc.add_paragraph("Texto local de teste")
        table = doc.add_table(rows=1, cols=2)
        table.cell(0, 0).text, table.cell(0, 1).text = "Campo", "Valor"
        doc.save(path)
        result = FileTools().read_document(path)
        self.assertIn("Texto local de teste", result)
        self.assertIn("Campo | Valor", result)

    def test_bad_pdf_reports_an_error(self):
        path = self.root / "ruim.pdf"
        path.write_bytes(b"not a PDF")
        with self.assertRaises(FileToolError):
            self.tools.read(path)


if __name__ == "__main__":
    unittest.main()
