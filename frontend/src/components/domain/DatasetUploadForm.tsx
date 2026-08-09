"use client";

import { useState, type FormEvent } from "react";

import { uploadDatasetAction } from "@/app/datasets/actions";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Field, controlClassName } from "@/components/ui/Field";
import { ErrorState } from "@/components/ui/States";
import { useToast } from "@/context/ToastContext";

export function DatasetUploadForm() {
  const { showToast } = useToast();
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const form = event.currentTarget;
    const formData = new FormData(form);

    setIsUploading(true);
    setErrorMessage("");

    const result = await uploadDatasetAction(formData);

    if (result.ok) {
      showToast(result.message);
      form.reset();
    } else {
      // Upload errors are also shown inline, since they explain how to fix the file.
      setErrorMessage(result.message);
      showToast("That file could not be uploaded.", "error");
    }

    setIsUploading(false);
  }

  return (
    <Card>
      <CardHeader
        title="Add your own jobs"
        description="A spreadsheet (CSV) with a column for title, company, location, description, and experience level."
      />
      <CardBody>
        <form onSubmit={handleSubmit} className="space-y-5">
          <Field
            label="Choose your file"
            htmlFor="dataset-file"
            hint="Up to 2 MB and 5,000 jobs. We read each description to find the skills."
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
            label="Give it a name"
            htmlFor="dataset-name"
            hint="Anything you like. Spaces become underscores."
          >
            <input
              id="dataset-name"
              name="dataset_name"
              type="text"
              required
              maxLength={120}
              placeholder="my job list"
              className={controlClassName}
            />
          </Field>

          {errorMessage ? (
            <ErrorState title="Upload failed" description={errorMessage} />
          ) : null}

          <Button type="submit" disabled={isUploading}>
            {isUploading ? "Uploading…" : "Add these jobs"}
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}
