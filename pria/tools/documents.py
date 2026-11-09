"""Bounded, local text extraction from PDF and DOCX files."""
from pathlib import Path

from pria.tools.files import FileToolError


class DocumentTools:
    MAX_BYTES = 32 * 1024 * 1024
    MAX_CHARS = 120_000

    def read(self, path: str | Path) -> str:
        file_path = Path(path).expanduser()
        if not file_path.is_file():
            raise FileToolError(f"O arquivo não existe ou não pode ser lido: {file_path}")
        if file_path.stat().st_size > self.MAX_BYTES:
            raise FileToolError("Documento acima do limite de 32 MiB.")
        suffix = file_path.suffix.casefold()
        try:
            if suffix == ".pdf":
                import pymupdf
                pages = []
                with pymupdf.open(file_path) as doc:
                    if doc.is_encrypted:
                        raise FileToolError("PDF protegido por senha; não tentei desbloqueá-lo.")
                    for number, page in enumerate(doc, 1):
                        pages.append(f"[Página {number}]\n{page.get_text()}")
                text = "\n\n".join(pages)
            elif suffix == ".docx":
                from docx import Document
                doc = Document(file_path)
                chunks = [p.text for p in doc.paragraphs if p.text.strip()]
                for table in doc.tables:
                    chunks.extend(" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows)
                text = "\n".join(chunks)
            else:
                raise FileToolError("Somente PDF e DOCX são extraídos por este módulo.")
        except FileToolError:
            raise
        except Exception as exc:
            raise FileToolError(f"Falha ao extrair {file_path.name}: {type(exc).__name__}: {exc}") from exc
        if not text.strip():
            return f"{file_path.name}: nenhum texto extraível (PDF digitalizado pode exigir OCR)."
        if len(text) > self.MAX_CHARS:
            text = text[:self.MAX_CHARS] + "\n[Texto truncado no limite de segurança.]"
        return f"Fonte: {file_path}\n{text}"
