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

# Configuration du logger pour le suivi en temps réel
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conformity-reports", tags=["conformity-reports"])

# --- HELPERS D'EXTRACTION ROBUSTE ---

def get_siren_from_obj(data: dict) -> str:
    """
    Extrait le SIREN (9 chiffres). 
    Si seul le SIRET est présent, récupère les 9 premiers chiffres.
    """
    val = data.get('siren') or data.get('siret')
    if not val:
        return ""
    # Nettoyage : enlève espaces et garde les 9 premiers caractères
    return str(val).replace(" ", "").strip()[:9]

def get_ttc_amount(data: dict) -> float:
    """
    Cherche le montant TTC en testant les différentes clés possibles 
    générées par l'IA (montant_ttc, amount_ttc, etc.)
    """
    for key in ['montant_ttc', 'amount_ttc', 'total_ttc', 'total_amount']:
        val = data.get(key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    return 0.0

# --- LOGIQUE DE GÉNÉRATION (SERVICE) ---

async def generate_gold_analysis(client_id: UUID, files: list) -> dict:
    """
    Analyse les fichiers Silver pour générer le rapport de conformité Gold.
    Gère la structure result -> data et les variations de clés.
    """
    docs = {}
    attestations = []  # Liste pour stocker plusieurs attestations (URSSAF, Fiscale, etc.)
    source_files_meta = []
    
    # 1. Sourcing et Extraction
    for f in files:
        if f.processing_status == "done":
            source_files_meta.append({
                "file_id": str(f.file_id),
                "type": f.type,
                "s3_raw_path": getattr(f, 's3_raw_path', None)
            })
            
            # Accès sécurisé à silver_content -> result -> data
            silver = f.silver_content if isinstance(f.silver_content, dict) else {}
            content = silver.get("result", {}).get("data", {})
            
            doc_type = f.type.lower()
            if "attestation" in doc_type:
                attestations.append(content)
            else:
                docs[doc_type] = content

    logger.info(f"[GOLD-GEN] Client {client_id}: {len(source_files_meta)} fichiers chargés.")

    checks = []
    errors = []

    # --- RÈGLES MÉTIER ---

    # A. Pivot SIREN (Récupéré depuis le KBIS)
    kbis = docs.get('kbis', {})
    siren_ref = get_siren_from_obj(kbis)
    
    if not siren_ref:
        msg = "SIREN de référence introuvable dans le KBIS (Données manquantes)."
        logger.error(f"[GOLD-GEN] {msg}")
        errors.append(msg)
    else:
        logger.info(f"[GOLD-GEN] SIREN de référence : {siren_ref}")

        # Comparaison SIREN Facture
        if 'facture' in docs:
            f_siren = get_siren_from_obj(docs['facture'])
            checks.append({
                "code": "SIREN_FACTURE",
                "label": "Cohérence SIREN Facture vs Kbis",
                "status": "pass" if f_siren == siren_ref else "fail",
                "details": {"Trouvé": f_siren, "Attendu": siren_ref}
            })

        # Comparaison SIREN Devis
        if 'devis' in docs:
            d_siren = get_siren_from_obj(docs['devis'])
            checks.append({
                "code": "SIREN_DEVIS",
                "label": "Cohérence SIREN Devis vs Kbis",
                "status": "pass" if d_siren == siren_ref else "fail",
                "details": {"Trouvé": d_siren, "Attendu": siren_ref}
            })

        # Comparaison SIREN Attestations (Vérifie si au moins une est valide)
        if attestations:
            att_ok = any(get_siren_from_obj(a) == siren_ref for a in attestations)
            checks.append({
                "code": "SIREN_ATTESTATION",
                "label": "Cohérence SIREN Attestations vs Kbis",
                "status": "pass" if att_ok else "fail",
                "details": {"Attendu": siren_ref, "Nombre analysé": len(attestations)}
            })

    # B. IBAN Match (Facture vs RIB)
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

    # C. Montants (Seuil de tolérance 5%)
    if 'facture' in docs and 'devis' in docs:
        mt_f = get_ttc_amount(docs['facture'])
        mt_d = get_ttc_amount(docs['devis'])
        
        diff = abs(mt_f - mt_d) / mt_d if mt_d > 0 else (1.0 if mt_f > 0 else 0.0)
        
        checks.append({
            "code": "AMOUNT_CHECK",
            "label": "Écart montant Facture/Devis < 5%",
            "status": "pass" if diff <= 0.05 else "warning",
            "details": {"Ecart": round(diff * 100, 2), "Facture": mt_f, "Devis": mt_d}
        })

    # D. Dates (Antériorité du devis)
    if 'facture' in docs and 'devis' in docs:
        date_f = docs['facture'].get('date')
        date_d = docs['devis'].get('date')
        if date_f and date_d:
            checks.append({
                "code": "DATE_ORDER",
                "label": "Antériorité du Devis sur la Facture",
                "status": "pass" if date_d <= date_f else "warning",
                "details": {"Date du Devis": date_d, "Date de la Facture": date_f}
            })

    # Calcul du statut global
    status_global = "fail" if any(c["status"] == "fail" for c in checks) else "pass"
    if not source_files_meta:
        status_global = "unknown"

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
            "missing_documents": [],
            "errors": errors
        }
    }

# --- ROUTES API ---

@router.post("", response_model=ConformityReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ConformityReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Vérification de propriété
    c = await client_repo.get_client(db, payload.client_id)
    if not c or str(c.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    # Récupération des fichiers
    files = await file_repo.list_files_for_client(db, payload.client_id)
    
    # Génération de l'analyse Gold
    gold_content = await generate_gold_analysis(payload.client_id, files)

    # Déduction du statut technique
    final_status = "done"
    if not files or not gold_content["meta"]["source_files"]:
        final_status = "error"

    # Sauvegarde en base
    return await report_repo.create_report(
        db,
        client_id=payload.client_id,
        gold_content=gold_content,
        s3_gold_path=None,
        silver_content=None,
        processing_status=final_status,
    )

@router.get("", response_model=List[ConformityReportRead])
async def list_reports(
    client_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    c = await client_repo.get_client(db, client_id)
    if not c or str(c.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return await report_repo.list_reports_for_client(db, client_id, skip=skip, limit=limit)

@router.get("/{report_id}", response_model=ConformityReportRead)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await report_repo.get_report(db, report_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    c = await client_repo.get_client(db, r.client_id)
    if not c or str(c.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return r

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await report_repo.get_report(db, report_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    c = await client_repo.get_client(db, r.client_id)
    if not c or str(c.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        
    await report_repo.delete_report(db, r)
    return None