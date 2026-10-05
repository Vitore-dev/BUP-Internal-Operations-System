import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import FinanceDocumentVersion

from accounts.decorators import role_required
from .models import (
    FinanceSourceFile, FinanceSourceFilePage,
    FinanceDocument, FinanceDocumentPage,
)
from .forms import SourceFileUploadForm, DocumentTitleForm
from .thumbnails import generate_source_file_pages, regenerate_document_version


@login_required
@role_required('FINANCE', 'ADMIN')
def document_list(request):
    query = request.GET.get('q', '').strip()
    documents = FinanceDocument.objects.all().order_by('-created_at')
    if query:
        documents = documents.filter(title__icontains=query)
    return render(request, 'finance/document_list.html', {
        'documents': documents, 'query': query,
    })
 


@login_required
@role_required('FINANCE', 'ADMIN')
def document_create(request):
    if request.method == 'POST':
        form = DocumentTitleForm(request.POST)
        if form.is_valid():
            document = form.save(commit=False)
            document.created_by = request.user
            document.save()
            return redirect('finance:document_builder', pk=document.pk)
    else:
        form = DocumentTitleForm()
    return render(request, 'finance/document_create.html', {'form': form})


@login_required
@role_required('FINANCE', 'ADMIN')
def document_builder(request, pk):
    """
    The drag-and-drop workspace. "Available Pages" is scoped to THIS
    document's own uploads only — not a shared library across every
    document in the system.
    """
    document = get_object_or_404(FinanceDocument, pk=pk)
    source_files = document.source_files.prefetch_related('pages').order_by('-uploaded_at')
    composition = document.pages.select_related('source_page__source_file').order_by('order')
    latest_version = document.versions.order_by('-version_number').first()
    upload_form = SourceFileUploadForm()
    return render(request, 'finance/document_builder.html', {
        'document': document,
        'source_files': source_files,
        'composition': composition,
        'latest_version': latest_version,
        'upload_form': upload_form,
    })


@login_required
@role_required('FINANCE', 'ADMIN')
def document_upload_source(request, pk):
    """
    Upload a PDF directly into this document's own page pool. Redirects
    back to the builder either way — errors show as a message banner
    rather than a separate page, since this is always reached from the
    builder's inline upload form.
    """
    document = get_object_or_404(FinanceDocument, pk=pk)
    if request.method == 'POST':
        form = SourceFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            source_file = form.save(commit=False)
            source_file.document = document
            source_file.uploaded_by = request.user
            source_file.save()
            generate_source_file_pages(source_file)
            messages.success(request, f"Uploaded — {source_file.page_count} page(s) ready to use.")
        else:
            messages.error(request, "Upload failed — check the file and try again.")
    return redirect('finance:document_builder', pk=pk)


@login_required
@role_required('FINANCE', 'ADMIN')
def document_save_composition(request, pk):
    """
    AJAX endpoint called by the builder's JS on every drop/removal.
    Body: {"page_ids": [<FinanceSourceFilePage id>, ...]} in the desired
    final order (duplicates allowed — e.g. a cover page used twice).
    Replaces this document's FinanceDocumentPage rows wholesale to match,
    then regenerates a new FinanceDocumentVersion from that ordering.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    document = get_object_or_404(FinanceDocument, pk=pk)
    try:
        payload = json.loads(request.body)
        page_ids = payload['page_ids']
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid payload'}, status=400)

    document.pages.all().delete()
    for index, source_page_id in enumerate(page_ids):
        # Guard against a stale/foreign page id reaching here instead of
        # a hard 404, which would otherwise abort mid-rebuild and leave
        # the composition half-written.
        source_page = FinanceSourceFilePage.objects.filter(
            pk=source_page_id, source_file__document=document
        ).first()
        if source_page is None:
            return JsonResponse({'error': f'Page {source_page_id} does not belong to this document.'}, status=400)
        FinanceDocumentPage.objects.create(document=document, source_page=source_page, order=index)

    if page_ids:
        version = regenerate_document_version(document, request.user)
        return JsonResponse({'ok': True, 'version_number': version.version_number, 'file_url': version.file.url})
    return JsonResponse({'ok': True, 'version_number': None, 'file_url': None})


@login_required
@role_required('FINANCE', 'ADMIN')
def document_versions(request, pk):
    document = get_object_or_404(FinanceDocument, pk=pk)
    versions = document.versions.order_by('-version_number')
    return render(request, 'finance/document_versions.html', {
        'document': document, 'versions': versions,
    })

@login_required
@role_required('FINANCE', 'ADMIN')
def document_version_delete(request, pk, version_pk):
    """
    Deletes one specific version permanently. This is the one place in
    the finance app that doesn't keep history — every other action here
    adds a new version rather than removing an old one. Confirmation
    happens via the template (a plain "Are you sure?" before the POST
    fires), not a separate confirmation page, since this is a single,
    low-traffic action.
    """
    document = get_object_or_404(FinanceDocument, pk=pk)
    version = get_object_or_404(FinanceDocumentVersion, pk=version_pk, document=document)
 
    if request.method == 'POST':
        version_number = version.version_number
        version.delete()
        messages.success(request, f"Version {version_number} deleted.")
        return redirect('finance:document_versions', pk=pk)
 
    return redirect('finance:document_versions', pk=pk)
 