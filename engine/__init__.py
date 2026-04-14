"""Document processing engine handlers."""
from engine.docx_handler import DocxHandler
from engine.txt_handler import TxtHandler
from engine.pdf_handler import PdfHandler
from engine.audit_engine import AuditEngine, AuditResult


def get_handler(file_path: str):
    """Get the appropriate handler based on file extension."""
    ext = file_path.rsplit('.', 1)[-1].lower()
    handlers = {
        'docx': DocxHandler(),
        'txt': TxtHandler(),
        'pdf': PdfHandler(),
    }
    handler = handlers.get(ext)
    if handler is None:
        raise ValueError(f"Unsupported file type: .{ext}")
    return handler


__all__ = ['DocxHandler', 'TxtHandler', 'PdfHandler', 'AuditEngine', 'AuditResult', 'get_handler']
