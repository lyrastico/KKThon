import logging
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.conformity_report import (
    ConformityReportCreate,
    ConformityReportRead,
)
import app.repositories.client as client_repo
import app.repositories.conformity_report as report_repo
import app.repositories.file as file_repo

# Configuration du logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conformity-reports", tags=["conformity-reports"])

# --- HELPERS D'EXTRACTION ---

def _uid(current_user) -> UUID:
    return UUID(str(current_user.id))

async def _client_owned(db, client_id: UUID, current_user):
    c = await client_repo.get_client(db, client_id)
    if not c or c.user_id != _uid(current_user):
        return None
    return c

def get_siren(data: dict) -> str:
    """Extrait le SIREN (9 chiffres) depuis siren, siret ou TVA."""
    val = data.get('siren') or data.get('siret')
    if not val and data.get('tva'):
        tva = str(data.get('tva')).replace(" ", "")
        if len(tva) >= 11: val = tva[-9:]
    if not val: return ""
    return str(val).replace(" ", "").strip()[:9]

def get_ttc_amount(data: dict) -> float:
    """Extrait le montant TTC via plusieurs clés possibles."""
    for key in ['montant_ttc', 'amount_ttc', 'total_ttc', 'total_amount']:
        if data.get(key) is not None:
            try: return float(data.get(key))
            except: continue
    return 0.0

def clean_text(val) -> str:
    """Normalise le texte pour comparaison."""
    if not val: return ""
    return str(val).strip().lower().replace(" ", "")

# --- MOTEUR DE GÉNÉRATION (LOGIQUE DE CONSENSUS) ---

async def generate_gold_analysis(client_id: UUID, files: list) -> dict:
    docs_data = []
    source_files_meta = []
    
    for f in files:
        if f.processing_status == "done":
            # On utilise f.file_id car tes logs montrent que c'est le nom du champ
            source_files_meta.append({
                "file_id": str(f.file_id),
                "type": f.type,
                "s3_raw_path": getattr(f, 's3_raw_path', None)
            })
            
            silver = f.silver_content if isinstance(f.silver_content, dict) else {}
            content = silver.get("result", {}).get("data", {}) or silver.get("data", {})
            
            doc_info = {
                "type": f.type.lower() if f.type else "inconnu",
                "file_id": str(f.file_id),
                "siren": get_siren(content),
                "amount": get_ttc_amount(content),
                "date": content.get('date') or content.get('date_edition'),
                "raison_sociale": content.get('raison_sociale') or content.get('denomination'),
                "iban": str(content.get('iban', "")).replace(" ", "").upper(),
                "raw_content": content
            }
            docs_data.append(doc_info)

    checks = []
    errors = []

    if not docs_data:
        return {
            "meta": {"client_id": str(client_id), "generated_at": datetime.utcnow().isoformat(), "source_files": []},
            "results": {"status_global": "error", "checks": [], "errors": ["Aucun fichier traité trouvé."]}
        }

    # 1. CONSENSUS SIREN STRICT (TOUS les documents)
    sirens_found = [d['siren'] for d in docs_data if d['siren']]
    if not sirens_found:
        errors.append("Aucun identifiant (SIREN/SIRET) trouvé dans les documents.")
    else:
        ref_siren = sirens_found[0]
        all_match = True
        for doc in docs_data:
            if doc['siren']:
                match = (doc['siren'] == ref_siren)
                if not match: all_match = False
                checks.append({
                    "code": f"SIREN_CHECK_{doc['type'].upper()}",
                    "label": f"Cohérence SIREN : {doc['type']}",
                    "status": "pass" if match else "fail",
                    "details": {"found": doc['siren'], "expected": ref_siren}
                })
        if not all_match:
            errors.append("Conflit d'identité : Les SIREN ne sont pas identiques sur tous les documents.")

    # 2. RAISON SOCIALE
    names = [d for d in docs_data if d['raison_sociale']]
    if len(names) > 1:
        ref_name = clean_text(names[0]['raison_sociale'])
        for n in names[1:]:
            curr = clean_text(n['raison_sociale'])
            is_ok = ref_name in curr or curr in ref_name
            checks.append({
                "code": f"NAME_CHECK_{n['type'].upper()}",
                "label": f"Raison Sociale : {n['type']}",
                "status": "pass" if is_ok else "warning",
                "details": {"found": n['raison_sociale'], "ref": names[0]['raison_sociale']}
            })

    # 3. IBAN (Facture vs RIB)
    facture = next((d for d in docs_data if "facture" in d['type']), None)
    rib = next((d for d in docs_data if "rib" in d['type']), None)
    if facture and rib:
        match = (facture['iban'] == rib['iban'] and rib['iban'] != "")
        checks.append({
            "code": "IBAN_COHERENCE",
            "label": "IBAN : Facture vs RIB",
            "status": "pass" if match else "fail",
            "details": {"match": match}
        })

    # 4. MONTANTS (Facture vs Devis)
    devis = next((d for d in docs_data if "devis" in d['type']), None)
    if facture and devis:
        mt_f, mt_d = facture['amount'], devis['amount']
        diff = abs(mt_f - mt_d) / mt_d if mt_d > 0 else (1.0 if mt_f > 0 else 0.0)
        checks.append({
            "code": "AMOUNT_CONSISTENCY",
            "label": "Montant TTC : Facture vs Devis",
            "status": "pass" if diff <= 0.05 else "warning",
            "details": {"diff_percent": round(diff * 100, 2), "invoice": mt_f, "quote": mt_d}
        })

    # 5. DATES ET VALIDITÉ
    if facture and facture['date']:
        f_date = facture['date']
        if devis and devis['date']:
            checks.append({
                "code": "DATE_CHRONOLOGY",
                "label": "Chronologie Devis/Facture",
                "status": "pass" if devis['date'] <= f_date else "warning",
                "details": {"devis": devis['date'], "facture": f_date}
            })
        
        attestations = [d for d in docs_data if "attestation" in d['type']]
        if attestations:
            is_valid = any((a['raw_content'].get('date_validite') or a['raw_content'].get('periode_fin') or "0") >= f_date for a in attestations)
            checks.append({
                "code": "LEGAL_VALIDITY",
                "label": "Attestations à jour",
                "status": "pass" if is_valid else "warning",
                "details": {"invoice_date": f_date}
            })

    status_global = "pass"
    if any(c["status"] == "fail" for c in checks) or errors: status_global = "fail"
    elif any(c["status"] == "warning" for c in checks): status_global = "warning"

    return {
        "meta": {"client_id": str(client_id), "generated_at": datetime.utcnow().isoformat(), "source_files": source_files_meta},
        "results": {"status_global": status_global, "checks": checks, "errors": errors}
    }

# --- ROUTES (FIXÉES) ---

@router.post("", response_model=ConformityReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ConformityReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not await _client_owned(db, payload.client_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    files = await file_repo.list_files_for_client(db, payload.client_id)
    gold_content = await generate_gold_analysis(payload.client_id, files)

    final_status = "done" if files and gold_content["meta"]["source_files"] else "error"

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