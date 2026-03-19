from uuid import UUID
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.conformity_report import (
    ConformityReportCreate,
    ConformityReportRead,
    ConformityReportUpdate,
)
import app.repositories.client as client_repo
import app.repositories.conformity_report as report_repo
import app.repositories.file as file_repo

router = APIRouter(prefix="/conformity-reports", tags=["conformity-reports"])

# --- HELPERS ---

def _uid(current_user) -> UUID:
    return UUID(str(current_user.id))

async def _client_owned(db, client_id: UUID, current_user):
    c = await client_repo.get_client(db, client_id)
    if not c or c.user_id != _uid(current_user):
        return None
    return c

# --- LOGIQUE DE GÉNÉRATION (SERVICE) ---

async def generate_gold_analysis(client_id: UUID, files: list) -> dict:
    """
    Génère le contenu Gold complet selon la spec :
    - Meta, Results (checks, missing, errors), Traceability.
    """
    docs = {}
    source_files_meta = []
    
    # 1. Sourcing : Filtrage 'done' et Snapshot des sources
    for f in files:
        if f.processing_status == "done":
            source_files_meta.append({
                "file_id": str(f.id),
                "type": f.type,
                "s3_raw_path": getattr(f, 's3_raw_path', None),
                "s3_silver_path": getattr(f, 's3_silver_path', None)
            })
            # Extraction du contenu silver (on supporte {'data': {...}} ou le dict direct)
            content = f.silver_content.get("data", {}) if isinstance(f.silver_content, dict) else (f.silver_content or {})
            docs[f.type.lower()] = content

    checks = []
    missing_docs = []
    errors = []

    # --- RÈGLES MÉTIER ---

    # A. Pivot SIREN (KBIS obligatoire pour comparer)
    kbis_data = docs.get('kbis', {})
    siren_ref = str(kbis_data.get('siren', "")).replace(" ", "").strip()
    
    if not siren_ref:
        errors.append("SIREN de référence introuvable dans le KBIS (ou KBIS manquant).")

    for t in ['facture', 'devis', 'attestation']:
        if t in docs:
            val = str(docs[t].get('siren', "")).replace(" ", "").strip()
            is_ok = (val == siren_ref and val != "")
            checks.append({
                "code": f"SIREN_{t.upper()}",
                "label": f"Cohérence SIREN {t.capitalize()} vs Kbis",
                "status": "pass" if is_ok else "fail",
                "details": {"found": val, "expected": siren_ref}
            })
        else:
            missing_docs.append(t.capitalize())

    # B. IBAN Match
    if 'facture' in docs and 'rib' in docs:
        iban_f = str(docs['facture'].get('iban', "")).replace(" ", "").upper()
        iban_r = str(docs['rib'].get('iban', "")).replace(" ", "").upper()
        is_iban_ok = (iban_f == iban_r and iban_f != "")
        checks.append({
            "code": "IBAN_MATCH",
            "label": "IBAN Facture conforme au RIB",
            "status": "pass" if is_iban_ok else "fail",
            "details": {"match": is_iban_ok}
        })

    # C. Montants (Seuil 5%)
    if 'facture' in docs and 'devis' in docs:
        try:
            mt_f = float(docs['facture'].get('amount_ttc', 0))
            mt_d = float(docs['devis'].get('amount_ttc', 0))
            diff = abs(mt_f - mt_d) / mt_d if mt_d > 0 else 1
            checks.append({
                "code": "AMOUNT_CHECK",
                "label": "Écart montant Facture/Devis < 5%",
                "status": "pass" if diff <= 0.05 else "warning",
                "details": {"diff_percent": round(diff * 100, 2), "invoice": mt_f, "quote": mt_d}
            })
        except Exception as e:
            errors.append(f"Erreur calcul montants: {str(e)}")

    # D. Dates (Antériorité)
    if 'facture' in docs and 'devis' in docs:
        df, dd = docs['facture'].get('date'), docs['devis'].get('date')
        if df and dd:
            checks.append({
                "code": "DATE_ORDER",
                "label": "Antériorité du Devis sur la Facture",
                "status": "pass" if dd <= df else "warning",
                "details": {"quote_date": dd, "invoice_date": df}
            })

    # Résultat Global
    status_global = "fail" if any(c["status"] == "fail" for c in checks) else "pass"
    if not source_files_meta:
        status_global = "unknown"
        errors.append("Aucun fichier traité ('done') trouvé pour ce client.")

    return {
        "meta": {
            "client_id": str(client_id),
            "generated_at": datetime.utcnow().isoformat(),
            "rule_set_version": "v1",
            "source_files": source_files_meta
        },
        "results": {
            "status_global": status_global,
            "checks": checks,
            "missing_documents": missing_docs,
            "errors": errors
        }
    }

# --- ROUTES ---

@router.post("", response_model=ConformityReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ConformityReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /conformity-reports
    Génère un rapport Gold basé sur les fichiers Silver existants.
    """
    # 1. Vérification Propriété
    if not await _client_owned(db, payload.client_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    # 2. Force : Optionnel (gestion de la suppression si nécessaire)
    # if payload.force:
    #     await report_repo.delete_reports_for_client(db, payload.client_id)

    # 3. Récupération des fichiers du client
    files = await file_repo.list_files_for_client(db, payload.client_id)

    # 4. Génération automatique du contenu Gold (Logique métier)
    gold_content = await generate_gold_analysis(payload.client_id, files)

    # 5. Mode Dry Run : On renvoie le calcul sans sauver
    if getattr(payload, 'dry_run', False):
        return ConformityReportRead(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            client_id=payload.client_id,
            gold_content=gold_content,
            processing_status="dry_run",
            created_at=datetime.utcnow()
        )

    # 6. Déduction du statut technique (done par défaut si le process tourne)
    final_status = "done"
    if not files or not gold_content["meta"]["source_files"]:
        final_status = "error"

    # 7. Création en base (silver_content reste NULL)
    return await report_repo.create_report(
        db,
        client_id=payload.client_id,
        gold_content=gold_content,
        s3_gold_path=None,
        silver_content=None,
        processing_status=final_status,
    )

@router.get("", response_model=list[ConformityReportRead])
async def list_reports(
    client_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    if not await _client_owned(db, client_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return await report_repo.list_reports_for_client(db, client_id, skip=skip, limit=limit)

@router.get("/{report_id}", response_model=ConformityReportRead)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await report_repo.get_report(db, report_id)
    if not r or not await _client_owned(db, r.client_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return r

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await report_repo.get_report(db, report_id)
    if not r or not await _client_owned(db, r.client_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    await report_repo.delete_report(db, r)
    return None