"""
Transcription tests — image-to-text and document saving.
"""

import shutil
import tempfile
from pathlib import Path

from src.config import config


class TestTranscription:
    def test_text_file_passthrough(self):
        from src.tools.transcription import transcribe_document_image
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("Hello world")
            tmp = f.name
        try:
            result = transcribe_document_image(tmp)
            assert "Hello world" in result
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_missing_file_returns_error(self):
        from src.tools.transcription import transcribe_document_image
        result = transcribe_document_image("/nonexistent/file.png")
        assert "Error" in result

    def test_image_without_api_key(self):
        from src.tools.transcription import transcribe_document_image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG")
            tmp = f.name
        try:
            result = transcribe_document_image(tmp)
            assert "OCR Notice" in result or "Notice" in result
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_translate_prompt_included(self):
        from src.tools.transcription import transcribe_document_image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG")
            tmp = f.name
        try:
            result = transcribe_document_image(tmp, target_language="Translate to English")
            # Without API key, still shows OCR Notice
            assert "OCR Notice" in result or "Notice" in result
        finally:
            Path(tmp).unlink(missing_ok=True)


class TestTranscribedDocumentSave:
    def test_saves_md_to_project(self):
        from src.ingestion import save_transcribed_document

        result = save_transcribed_document("ocr_user", "ocr_proj", "scan.png", "Transcribed content.")
        assert "Successfully saved" in result
        doc_dir = config.project_root / "data" / "users" / "ocr_user" / "projects" / "ocr_proj" / "documents"
        saved = doc_dir / "scan_transcript.md"
        assert saved.exists()
        assert "Transcribed content." in saved.read_text()
        shutil.rmtree(config.project_root / "data" / "users" / "ocr_user", ignore_errors=True)

    def test_empty_content_returns_error(self):
        from src.ingestion import save_transcribed_document
        result = save_transcribed_document("u", "p", "file.png", "")
        assert "Error" in result
