import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from core.utils import log_action
from .models import FinanceDocument, FinanceDocumentPage

logger = logging.getLogger('finance.documents')


def _files_of(document):
    """Every file on disk that belongs to this document, as (storage, name) pairs."""
    files = []
    for version in document.versions.all():
        if version.file:
            files.append((version.file.storage, version.file.name))
    for source in document.source_files.all():
        if source.file:
            files.append((source.file.storage, source.file.name))
        for page in source.pages.all():
            if page.thumbnail:
                files.append((page.thumbnail.storage, page.thumbnail.name))
    return files


@login_required
@role_required('FINANCE', 'ADMIN')
def document_delete(request, pk):
    """
    Permanently deletes a finance document: its saved versions, the files uploaded into it,
    and the page thumbnails. A GET only shows the confirmation page; nothing is deleted until a POST.
    """
    document = get_object_or_404(FinanceDocument, pk=pk)

    if request.method == 'POST':
        title = document.title
        versions = document.versions.count()
        sources = document.source_files.count()
        files = _files_of(document)    # worked out BEFORE the rows are gone

        try:
            with transaction.atomic():
                # A composition points at source pages with PROTECT, so it has to be removed first;
                # otherwise the database refuses to delete the pages it uses.
                FinanceDocumentPage.objects.filter(document=document).delete()
                document.source_files.all().delete()    # takes the page thumbnails' rows with it
                document.delete()                        # takes the saved versions with it
        except ProtectedError:
            messages.error(request, 'This document could not be deleted because another document still uses some of its pages.')
            return redirect('finance:document_list')

        # Only now that the database has let go, remove the files from disk. A missing file is not an error.
        removed = 0
        for storage, name in files:
            try:
                storage.delete(name)
                removed += 1
            except Exception:
                logger.exception("Could not remove %s after deleting finance document %s", name, pk)

        log_action(request, 'FINANCE_DOCUMENT_DELETED',
                   description=f'{request.user} permanently deleted the finance document "{title}" (#{pk}): '
                               f'{versions} saved version(s), {sources} uploaded file(s), {removed} file(s) removed from disk.')
        messages.success(request, f'"{title}" was deleted.')
        return redirect('finance:document_list')

    return render(request, 'finance/document_confirm_delete.html', {
        'document': document,
        'version_count': document.versions.count(),
        'source_count': document.source_files.count(),
    })
