import fitz  # PyMuPDF
from io import BytesIO
from django.core.files.base import ContentFile

THUMBNAIL_WIDTH_PX = 300


def generate_source_file_pages(source_file):
    """
    Called once, right after a FinanceSourceFile is uploaded. Opens the
    PDF, records its real page count, and renders one thumbnail PNG per
    page — this is what the builder UI's drag-and-drop grid is built
    from, never the raw PDF pages directly.
    """
    from .models import FinanceSourceFilePage

    source_file.file.open('rb')
    doc = fitz.open(stream=source_file.file.read(), filetype='pdf')
    source_file.file.close()

    source_file.page_count = doc.page_count
    source_file.save(update_fields=['page_count'])

    for page_number in range(doc.page_count):
        page = doc[page_number]
        zoom = THUMBNAIL_WIDTH_PX / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        thumb_bytes = pix.tobytes('png')

        page_obj = FinanceSourceFilePage(source_file=source_file, page_number=page_number)
        page_obj.thumbnail.save(
            f"sf{source_file.pk}_p{page_number}.png",
            ContentFile(thumb_bytes),
            save=False,
        )
        page_obj.save()

    doc.close()


def regenerate_document_version(document, user):
    """
    Rebuilds the merged PDF from the document's CURRENT FinanceDocumentPage
    ordering and saves it as the next FinanceDocumentVersion. Called after
    every add/remove/reorder operation from the builder UI — the
    composition table is the source of truth, this just renders it.
    """
    from .models import FinanceDocumentVersion

    pages = document.pages.select_related('source_page__source_file').order_by('order')

    out = fitz.open()
    open_sources = {}  # cache: don't reopen the same source PDF twice per regeneration
    try:
        for dp in pages:
            source_page = dp.source_page
            sf = source_page.source_file
            if sf.pk not in open_sources:
                sf.file.open('rb')
                open_sources[sf.pk] = fitz.open(stream=sf.file.read(), filetype='pdf')
                sf.file.close()
            src_doc = open_sources[sf.pk]
            out.insert_pdf(src_doc, from_page=source_page.page_number, to_page=source_page.page_number)

        buffer = BytesIO()
        out.save(buffer)
    finally:
        out.close()
        for d in open_sources.values():
            d.close()

    buffer.seek(0)

    last_version = document.versions.order_by('-version_number').first()
    next_number = (last_version.version_number + 1) if last_version else 1

    version = FinanceDocumentVersion(document=document, version_number=next_number, created_by=user)
    version.file.save(f"doc{document.pk}_v{next_number}.pdf", ContentFile(buffer.read()), save=False)
    version.save()
    return version
