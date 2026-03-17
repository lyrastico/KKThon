"""
## Process Document OCR (S3 -> Document AI -> Bronze)

This DAG is triggered via the Airflow REST API when a document is uploaded to S3.
It downloads the document from S3, extracts text using Google Document AI OCR,
and stores the structured result in the bronze zone of S3.

Expected `dag_run.conf`:
{
    "bucket": "s3-agdt-202077714167-eu-north-1-an",
    "key": "raw/document.pdf"
}
"""

from __future__ import annotations

import base64
import json
import mimetypes
from datetime import datetime as dt
from pathlib import Path

from airflow.sdk import dag, task
from pendulum import datetime


DOCUMENT_AI_PROJECT_ID = "971677530421"
DOCUMENT_AI_LOCATION = "eu"
DOCUMENT_AI_PROCESSOR_ID = "42d5d89ccd74b863"

S3_CONN_ID = "s3_bucket_medaillon"
GCP_CONN_ID = "document_ai"


@dag(
    dag_id="process_document_ocr",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["ocr", "document-ai", "s3", "event-driven"],
    doc_md=__doc__,
)
def process_document_ocr():

    @task
    def download_from_s3(**context) -> dict:
        """Download document from S3 and return its content as base64."""
        from airflow.providers.amazon.aws.hooks.s3 import S3Hook

        conf = (context.get("dag_run").conf if context.get("dag_run") else {}) or {}
        bucket = conf.get("bucket")
        key = conf.get("key")

        if not bucket or not key:
            raise ValueError(f"Missing bucket or key in dag_run.conf: {conf}")

        print(f"Downloading s3://{bucket}/{key}")

        s3_hook = S3Hook(aws_conn_id=S3_CONN_ID)
        s3_obj = s3_hook.get_key(key=key, bucket_name=bucket)
        file_bytes = s3_obj.get()["Body"].read()

        mime_type, _ = mimetypes.guess_type(key)
        if mime_type is None:
            mime_type = "application/pdf"

        print(f"Downloaded {len(file_bytes)} bytes, mime_type={mime_type}")

        return {
            "bucket": bucket,
            "key": key,
            "content_base64": base64.b64encode(file_bytes).decode("utf-8"),
            "mime_type": mime_type,
        }

    @task
    def extract_text_with_document_ai(s3_data: dict) -> dict:
        """Send document to Google Document AI for OCR and extract text."""
        from google.cloud import documentai_v1 as documentai
        from airflow.providers.google.common.hooks.base_google import GoogleBaseHook

        gcp_hook = GoogleBaseHook(gcp_conn_id=GCP_CONN_ID)
        credentials = gcp_hook.get_credentials()

        client_options = {"api_endpoint": f"{DOCUMENT_AI_LOCATION}-documentai.googleapis.com"}
        client = documentai.DocumentProcessorServiceClient(
            credentials=credentials,
            client_options=client_options,
        )

        file_bytes = base64.b64decode(s3_data["content_base64"])
        mime_type = s3_data["mime_type"]

        raw_document = documentai.RawDocument(content=file_bytes, mime_type=mime_type)

        processor_name = client.processor_path(
            DOCUMENT_AI_PROJECT_ID,
            DOCUMENT_AI_LOCATION,
            DOCUMENT_AI_PROCESSOR_ID,
        )

        print(f"Calling Document AI processor: {processor_name}")

        request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)
        result = client.process_document(request=request)
        document = result.document

        extracted_text = document.text
        page_count = len(document.pages)

        confidence_scores = []
        for page in document.pages:
            for block in page.blocks:
                if block.layout.confidence:
                    confidence_scores.append(block.layout.confidence)

        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else None

        print(f"Extracted {len(extracted_text)} characters from {page_count} pages")

        return {
            "bucket": s3_data["bucket"],
            "key": s3_data["key"],
            "mime_type": s3_data["mime_type"],
            "text": extracted_text,
            "page_count": page_count,
            "confidence": avg_confidence,
        }

    @task
    def save_to_bronze(ocr_result: dict) -> dict:
        """Save OCR result as JSON to the bronze zone in S3."""
        from airflow.providers.amazon.aws.hooks.s3 import S3Hook

        source_key = ocr_result["key"]
        filename = Path(source_key).stem
        bronze_key = f"bronze/{filename}.json"

        result_json = {
            "source": {
                "bucket": ocr_result["bucket"],
                "key": ocr_result["key"],
                "mime_type": ocr_result["mime_type"],
            },
            "processing": {
                "processor_id": DOCUMENT_AI_PROCESSOR_ID,
                "processor_type": "DOCUMENT_OCR",
                "processed_at": dt.utcnow().isoformat() + "Z",
            },
            "result": {
                "text": ocr_result["text"],
                "page_count": ocr_result["page_count"],
                "confidence": ocr_result["confidence"],
            },
        }

        json_bytes = json.dumps(result_json, ensure_ascii=False, indent=2).encode("utf-8")

        s3_hook = S3Hook(aws_conn_id=S3_CONN_ID)
        s3_hook.load_bytes(
            bytes_data=json_bytes,
            key=bronze_key,
            bucket_name=ocr_result["bucket"],
            replace=True,
        )

        print(f"Saved OCR result to s3://{ocr_result['bucket']}/{bronze_key}")

        return {
            "bronze_bucket": ocr_result["bucket"],
            "bronze_key": bronze_key,
            "size_bytes": len(json_bytes),
        }

    @task
    def log_result(bronze_info: dict) -> dict:
        """Log the final result and return summary."""
        print("=" * 50)
        print("OCR Processing Complete")
        print("=" * 50)
        print(f"Output: s3://{bronze_info['bronze_bucket']}/{bronze_info['bronze_key']}")
        print(f"Size: {bronze_info['size_bytes']} bytes")
        print("=" * 50)

        return bronze_info

    s3_data = download_from_s3()
    ocr_result = extract_text_with_document_ai(s3_data)
    bronze_info = save_to_bronze(ocr_result)
    log_result(bronze_info)


process_document_ocr()
