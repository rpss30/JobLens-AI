"use client";

import { useState, type FormEvent } from "react";

import { uploadDatasetAction } from "@/app/datasets/actions";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Field, controlClassName } from "@/components/ui/Field";
import { ErrorState } from "@/components/ui/States";

export function DatasetUploadForm() {
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const form = event.currentTarget;
    const formData = new FormData(form);

    setIsUploading(true);
    setErrorMessage("");
    setSuccessMessage("");

    const result = await uploadDatasetAction(formData);

    if (result.ok) {
      setSuccessMessage(result.message);
      form.reset();
    } else {
      setErrorMessage(result.message);
    }

    setIsUploading(false);
  }

  return (
    <Card>
      <CardHeader
        title="Upload a dataset"
        description="A jobs CSV with title, company, location, description, and experience_level columns."
      />
      <CardBody>
        <form onSubmit={handleSubmit} className="space-y-5">
          <Field
            label="Jobs CSV"
            htmlFor="dataset-file"
            hint="Up to 2 MB and 5,000 rows. Skills are extracted during processing."
          >
            <input
              id="dataset-file"
              name="file"
              type="file"
              accept=".csv,text/csv"
              required
              className="w-full text-sm text-text file:mr-3 file:rounded-lg file:border file:border-border-strong file:bg-surface file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-text hover:file:bg-surface-muted"
            />
          </Field>

          <Field
            label="Dataset name"
            htmlFor="dataset-name"
            hint="Saved as a lowercase, underscore-separated slug."
          >
            <input
              id="dataset-name"
              name="dataset_name"
              type="text"
              required
              maxLength={120}
              placeholder="my_custom_dataset"
              className={controlClassName}
            />
          </Field>

          {errorMessage ? (
            <ErrorState title="Upload failed" description={errorMessage} />
          ) : null}

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={isUploading}>
              {isUploading ? "Uploading…" : "Upload dataset"}
            </Button>
            <p role="status" className="text-sm text-text-muted">
              {successMessage}
            </p>
          </div>
        </form>
      </CardBody>
    </Card>
  );
}
