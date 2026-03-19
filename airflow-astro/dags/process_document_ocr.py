"""
## Process Document OCR (S3 -> Document AI -> Bronze/Silver)

This DAG is triggered via the Airflow REST API when a document is uploaded to S3.
It downloads the document from S3, extracts text using Google Document AI OCR,
stores the OCR output in the bronze zone, then sends the OCR text to Gemini 2.5 Flash
to extract structured fields and stores the JSON result in the silver zone.

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
import re
import urllib.parse
from datetime import datetime as dt
from pathlib import Path

from airflow.sdk import dag, task
from pendulum import datetime


DOCUMENT_AI_PROJECT_ID = "971677530421"
DOCUMENT_AI_LOCATION = "eu"
DOCUMENT_AI_PROCESSOR_ID = "42d5d89ccd74b863"

S3_CONN_ID = "s3_bucket_medaillon"
GCP_CONN_ID = "document_ai"
SUPABASE_CONN_ID = "supabase_access"

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GEMINI_SCOPES = ["https://www.googleapis.com/auth/generative-language"]


GEMINI_PROMPT = """
# RÔLE

Tu es un agent spécialisé dans l'extraction de données structurées à partir de textes OCR de documents administratifs français. Ta mission est d'identifier le type de document et d'extraire les informations pertinentes avec une précision absolue.



# INSTRUCTIONS DE TRAITEMENT

1. IDENTIFICATION : Analyse le texte pour déterminer s'il s'agit d'une Facture, d'un Devis, d'une Attestation (Vigilance/URSSAF), d'un Kbis ou d'un RIB.

2. EXTRACTION : Extraie uniquement les champs définis dans le référentiel ci-dessous.

3. FORMATAGE : 

   - SIRET/SIREN : Supprimer les espaces (ex: 12345678900012).

   - Montants : Float pur (ex: 1250.50), sans devise.

   - Dates : Format ISO 8601 (YYYY-MM-DD).

   - IBAN : Majuscules, sans espaces.

   - ABSENCE : Si une donnée est manquante ou illisible, renvoyer `null`.



# RÉFÉRENTIEL DES CHAMPS PAR DOCUMENT

- Facture : {siret, raison_sociale, adresse, montant_ttc, tva, date, iban, num_devis}

- Devis : {siret, raison_sociale, montant_ttc, date}

- Attestation : {siren, raison_sociale, date_validite, code_verification}

- Kbis : {siren, raison_sociale, adresse_siege}

- RIB : {iban, titulaire_compte}



# CONTRAINTES DE SORTIE

- Réponds EXCLUSIVEMENT sous forme d'un objet JSON unique.

- Ne pas ajouter de commentaires, de texte d'introduction ou de conclusion.

- Respecte strictement le schéma suivant :



{

  "document_detected": "Facture | Devis | Attestation | Kbis | RIB | Inconnu",

  "confidence_score": 0.00,

  "data": {

    "champ_1": "valeur",

    "champ_2": "valeur"

  }

}



# TEXTE OCR À ANALYSER
""".strip()


def _filename_stem_from_s3_key(key: str) -> str:
    return Path(key).stem


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


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
        filename = _filename_stem_from_s3_key(source_key)
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
    def extract_structured_with_gemini(ocr_result: dict) -> dict:
        """Send OCR text to Gemini to extract a structured JSON payload."""
        import requests

        from airflow.providers.google.common.hooks.base_google import GoogleBaseHook
        from google.auth.transport.requests import Request

        gcp_hook = GoogleBaseHook(gcp_conn_id=GCP_CONN_ID)
        credentials = gcp_hook.get_credentials()
        if hasattr(credentials, "with_scopes"):
            credentials = credentials.with_scopes(GEMINI_SCOPES)
        credentials.refresh(Request())

        access_token = credentials.token
        if not access_token:
            raise RuntimeError("Failed to obtain access token for Gemini API")

        ocr_text = ocr_result.get("text") or ""

        prompt = (
            GEMINI_PROMPT
            + "\n\n"
            + ocr_text
            + "\n\nRappels: réponds uniquement par un JSON unique, sans ```."
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        resp = requests.post(GEMINI_ENDPOINT, headers=headers, json=payload, timeout=180)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

        response_json = resp.json()
        try:
            model_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise RuntimeError(f"Unexpected Gemini response shape: {response_json}") from e

        parsed_text = _strip_json_fences(model_text)
        try:
            structured = json.loads(parsed_text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Gemini returned non-JSON content: {model_text}") from e

        allowed_docs = {"Facture", "Devis", "Attestation", "Kbis", "RIB", "Inconnu"}
        doc_type = structured.get("document_detected")
        if doc_type not in allowed_docs:
            structured["document_detected"] = "Inconnu"

        try:
            structured["confidence_score"] = float(structured.get("confidence_score", 0.0))
        except Exception:
            structured["confidence_score"] = 0.0

        if not isinstance(structured.get("data"), dict):
            structured["data"] = {}

        return {
            "source": {
                "bucket": ocr_result["bucket"],
                "key": ocr_result["key"],
                "mime_type": ocr_result["mime_type"],
            },
            "processing": {
                "model": GEMINI_MODEL,
                "processed_at": dt.utcnow().isoformat() + "Z",
            },
            "result": structured,
        }

    @task
    def save_to_silver(gemini_result: dict) -> dict:
        """Save Gemini structured JSON to the silver zone in S3."""
        from airflow.providers.amazon.aws.hooks.s3 import S3Hook

        source_key = gemini_result["source"]["key"]
        filename = _filename_stem_from_s3_key(source_key)
        silver_key = f"silver/{filename}.json"

        json_bytes = json.dumps(gemini_result, ensure_ascii=False, indent=2).encode("utf-8")

        s3_hook = S3Hook(aws_conn_id=S3_CONN_ID)
        s3_hook.load_bytes(
            bytes_data=json_bytes,
            key=silver_key,
            bucket_name=gemini_result["source"]["bucket"],
            replace=True,
        )

        print(f"Saved Gemini result to s3://{gemini_result['source']['bucket']}/{silver_key}")

        return {
            "silver_bucket": gemini_result["source"]["bucket"],
            "silver_key": silver_key,
            "size_bytes": len(json_bytes),
        }

    @task
    def sync_to_supabase(gemini_result: dict) -> dict:
        """Update `public.files` row matching `s3_raw_path` with silver results."""
        import requests

        from airflow.hooks.base import BaseHook

        conn = BaseHook.get_connection(SUPABASE_CONN_ID)
        extra = conn.extra_dejson or {}

        supabase_url = extra.get("SUPABASE_URL")
        service_role_key = extra.get("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not service_role_key:
            raise ValueError(
                "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in connection extra for supabase_access"
            )

        s3_raw_path = (gemini_result.get("source") or {}).get("key")
        if not s3_raw_path:
            raise ValueError(f"Missing source.key in gemini_result: {gemini_result}")

        filename = _filename_stem_from_s3_key(str(s3_raw_path))
        s3_silver_path = f"silver/{filename}.json"
        document_type = (gemini_result.get("result") or {}).get("document_detected")

        # We patch (update) the existing row created by the backend on upload.
        # If no row matches, we fail the task.
        encoded_path = urllib.parse.quote(str(s3_raw_path), safe="")
        endpoint = f"{supabase_url.rstrip('/')}/rest/v1/files?s3_raw_path=eq.{encoded_path}"

        payload = {
            "s3_silver_path": s3_silver_path,
            "silver_content": gemini_result,
            "type": document_type,
            "processing_status": "done",
        }

        headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Return updated rows so we can detect missing match.
            "Prefer": "return=representation",
        }

        resp = requests.patch(endpoint, headers=headers, json=payload, timeout=60)
        if resp.status_code >= 300:
            raise RuntimeError(f"Supabase PostgREST PATCH failed {resp.status_code}: {resp.text}")

        updated = resp.json()
        if not isinstance(updated, list) or len(updated) == 0:
            # No row matched the filter -> fail as requested.
            raise RuntimeError(
                f"No Supabase row matched public.files.s3_raw_path={s3_raw_path!r} (cannot update)"
            )

        print(f"Updated Supabase files row for s3_raw_path={s3_raw_path}")
        return {
            "supabase_updated": True,
            "updated_count": len(updated),
            "s3_raw_path": s3_raw_path,
            "s3_silver_path": s3_silver_path,
        }

    @task
    def log_result(bronze_info: dict, silver_info: dict, supabase_info: dict) -> dict:
        """Log the final result and return summary."""
        print("=" * 50)
        print("OCR + Gemini Processing Complete")
        print("=" * 50)
        print(f"Bronze: s3://{bronze_info['bronze_bucket']}/{bronze_info['bronze_key']}")
        print(f"Bronze size: {bronze_info['size_bytes']} bytes")
        print(f"Silver: s3://{silver_info['silver_bucket']}/{silver_info['silver_key']}")
        print(f"Silver size: {silver_info['size_bytes']} bytes")
        print(f"Supabase updated: {supabase_info.get('supabase_updated')}")
        print(f"Supabase updated rows: {supabase_info.get('updated_count')}")
        print("=" * 50)

        return {"bronze": bronze_info, "silver": silver_info, "supabase": supabase_info}

    s3_data = download_from_s3()
    ocr_result = extract_text_with_document_ai(s3_data)

    # Branch 1: OCR -> Bronze (can run in parallel)
    bronze_info = save_to_bronze(ocr_result)

    # Branch 2: OCR -> Gemini -> Silver -> Supabase
    gemini_result = extract_structured_with_gemini(ocr_result)
    silver_info = save_to_silver(gemini_result)
    supabase_info = sync_to_supabase(gemini_result)

    # Final join after both branches are complete
    log_result(bronze_info, silver_info, supabase_info)


process_document_ocr()
