from __future__ import annotations

from django.conf import settings
from django.db import models


class Dataset(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    source_type = models.CharField(max_length=50)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "datasets"

    def __str__(self) -> str:
        return self.name


class JobPosting(models.Model):
    id = models.AutoField(primary_key=True)
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.DO_NOTHING,
        db_column="dataset_id",
        related_name="job_postings",
    )
    job_id = models.CharField(max_length=100, null=True, blank=True)
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField()
    experience_level = models.CharField(max_length=100)
    source = models.CharField(max_length=50, null=True, blank=True)
    source_url = models.CharField(max_length=1000, null=True, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)
    date_posted = models.CharField(max_length=100, null=True, blank=True)
    valid_through = models.CharField(max_length=100, null=True, blank=True)
    employment_type = models.CharField(max_length=100, null=True, blank=True)
    workplace_type = models.CharField(max_length=100, null=True, blank=True)
    is_remote = models.BooleanField(default=False)
    address_locality = models.CharField(max_length=255, null=True, blank=True)
    address_region = models.CharField(max_length=100, null=True, blank=True)
    address_country = models.CharField(max_length=100, null=True, blank=True)
    source_updated_at = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "job_postings"

    def __str__(self) -> str:
        return f"{self.title} at {self.company}"


class ProcessedJob(models.Model):
    id = models.AutoField(primary_key=True)
    job_posting = models.OneToOneField(
        JobPosting,
        on_delete=models.DO_NOTHING,
        db_column="job_posting_id",
        related_name="processed_job",
    )
    clean_title = models.CharField(max_length=255)
    clean_description = models.TextField()
    role_category = models.CharField(max_length=100)
    extracted_skills = models.JSONField(default=list)
    skills_text = models.TextField(default="")
    skill_extraction_provider = models.CharField(max_length=100, null=True, blank=True)
    skill_extraction_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "processed_jobs"

    def __str__(self) -> str:
        return self.clean_title


class IngestionRun(models.Model):
    id = models.AutoField(primary_key=True)
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.DO_NOTHING,
        db_column="dataset_id",
        related_name="ingestion_runs",
        null=True,
        blank=True,
    )
    source_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    total_sources = models.IntegerField(default=0)
    successful_sources = models.IntegerField(default=0)
    failed_sources = models.IntegerField(default=0)
    raw_job_count = models.IntegerField(default=0)
    processed_job_count = models.IntegerField(default=0)
    error_log = models.JSONField(default=list)
    run_metadata = models.JSONField(default=dict)

    class Meta:
        managed = False
        db_table = "ingestion_runs"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.source_type} ({self.status})"


class ExtractionResult(models.Model):
    id = models.AutoField(primary_key=True)
    processed_job = models.ForeignKey(
        ProcessedJob,
        on_delete=models.DO_NOTHING,
        db_column="processed_job_id",
        related_name="extraction_results",
    )
    provider = models.CharField(max_length=100)
    model = models.CharField(max_length=255, null=True, blank=True)
    prompt_version = models.CharField(max_length=100, null=True, blank=True)
    extracted_skills = models.JSONField(default=list)
    raw_response = models.TextField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "extraction_results"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.provider} extraction for processed job {self.processed_job_id}"


class ExtractionReview(models.Model):
    STATUS_OPEN = "open"
    STATUS_REVIEWED = "reviewed"
    RETRY_STATUS_REQUESTED = "requested"

    extraction_result_id = models.PositiveIntegerField(unique=True, db_index=True)
    status = models.CharField(max_length=30, default=STATUS_OPEN)
    note = models.TextField(blank=True)
    note_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_extraction_review_notes",
    )
    note_updated_by_username = models.CharField(max_length=150, blank=True)
    note_updated_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_extraction_results",
    )
    reviewed_by_username = models.CharField(max_length=150, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    retry_status = models.CharField(max_length=30, blank=True, default="")
    retry_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requested_extraction_retries",
    )
    retry_requested_by_username = models.CharField(max_length=150, blank=True)
    retry_requested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ops_extraction_reviews"
        indexes = [
            models.Index(fields=["status", "updated_at"]),
            models.Index(fields=["retry_status", "retry_requested_at"]),
        ]

    def __str__(self) -> str:
        return f"review state for extraction result {self.extraction_result_id}"


class OperationsAuditEvent(models.Model):
    ACTION_NOTE_SAVED = "extraction_note_saved"
    ACTION_MARKED_REVIEWED = "extraction_marked_reviewed"
    ACTION_RETRY_REQUESTED = "extraction_retry_requested"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="operations_audit_events",
    )
    actor_username = models.CharField(max_length=150)
    action = models.CharField(max_length=100, db_index=True)
    target_type = models.CharField(max_length=100, db_index=True)
    target_id = models.PositiveIntegerField(db_index=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ops_audit_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_type", "target_id", "created_at"]),
            models.Index(fields=["actor_username", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} on {self.target_type} {self.target_id}"
