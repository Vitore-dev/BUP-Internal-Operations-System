from django.db import models
from django.conf import settings


class FinanceDocument(models.Model):
    """The composed output — what Finance actually downloads/files."""
    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class FinanceSourceFile(models.Model):
    """
    A raw PDF Finance uploads, scoped to ONE FinanceDocument — uploading
    happens directly inside that document's builder page, not through a
    shared global library. An earlier version made every uploaded file
    reusable across every document, which meant every document's builder
    showed every file anyone had ever uploaded — unmanageable in
    practice. null=True exists only to support rows created before this
    field was added; every new upload always sets it.
    """
    document = models.ForeignKey(
        FinanceDocument,
        on_delete=models.CASCADE,
        related_name='source_files',
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to='finance_sources/')
    label = models.CharField(max_length=200, blank=True, help_text="e.g. 'Vendor Invoice #4521'")
    page_count = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label or self.file.name


class FinanceSourceFilePage(models.Model):
    """
    One thumbnail per page of a FinanceSourceFile, generated once at
    upload time (see finance/thumbnails.py). This is what the builder UI
    actually drags around — never the source file as a whole.
    """
    source_file = models.ForeignKey(FinanceSourceFile, on_delete=models.CASCADE, related_name='pages')
    page_number = models.PositiveIntegerField(help_text="0-indexed position within the source file")
    thumbnail = models.ImageField(upload_to='finance_thumbnails/')

    class Meta:
        ordering = ['page_number']
        unique_together = ('source_file', 'page_number')

    def __str__(self):
        return f"{self.source_file} — page {self.page_number + 1}"


class FinanceDocumentPage(models.Model):
    """
    The current composition of a FinanceDocument — one row per page in
    the final output, in order. Rearranging is just editing `order`;
    removing a page is deleting a row; inserting is adding one. This
    table is rebuilt wholesale on every save from the builder UI, then
    used to regenerate a new FinanceDocumentVersion.
    """
    document = models.ForeignKey(FinanceDocument, on_delete=models.CASCADE, related_name='pages')
    source_page = models.ForeignKey(FinanceSourceFilePage, on_delete=models.PROTECT, related_name='used_in')
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.document} — position {self.order}"


class FinanceDocumentVersion(models.Model):
    """
    Every regenerated PDF, kept forever. Nothing is ever deleted here —
    reverting a bad edit is just downloading (or re-pointing to) an
    earlier version; the composition tables above only reflect the
    *current* state, this table is the permanent history.
    """
    document = models.ForeignKey(FinanceDocument, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to='finance_documents/')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = ('document', 'version_number')

    def __str__(self):
        return f"{self.document} — v{self.version_number}"