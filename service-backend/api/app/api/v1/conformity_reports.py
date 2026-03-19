import logging
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Configuration du logger
logger = logging.getLogger(__name__)

# --- UTILS D'EXTRACTION ET NETTOYAGE ---

def get_siren(data: dict) -> str:
    """Extrait le SIREN (9 chiffres) depuis siren, siret ou TVA."""
    val = data.get('siren') or data.get('siret')
    if not val and data.get('tva'):
        tva = str(data.get('tva')).replace(" ", "")
        if len(tva) >= 11: val = tva[-9:] # Les 9 derniers chiffres du TVA FR
    
    if not val: return ""
    return str(val).replace(" ", "").strip()[:9]

def get_ttc_amount(data: dict) -> float:
    """Extrait le montant TTC via plusieurs clés possibles."""
    for key in ['montant_ttc', 'amount_ttc', 'total_ttc', 'total_amount']:
        if data.get(key) is not None:
            try: return float(data.get(key))
            except: continue
    return 0.0

def clean_text(val: Any) -> str:
    """Normalise le texte pour comparaison (minuscule, sans espaces)."""
    if not val: return ""
    return str(val).strip().lower().replace(" ", "")

# --- MOTEUR DE CONFORMITÉ (CONSENSUS GLOBAL) ---

async def generate_gold_analysis(client_id: UUID, files: list) -> dict:
    """
    Analyse de conformité robuste :
    Chaque document doit corroborer les autres. Un seul conflit invalide le lot.
    """
    docs_data = [] # Liste de tous les documents extraits
    source_files_meta = []
    
    # 1. Chargement et Normalisation
    for f in files:
        if f.processing_status == "done":
            silver = f.silver_content if isinstance(f.silver_content, dict) else {}
            # Support structure 'result' -> 'data'
            content = silver.get("result", {}).get("data", {}) or silver.get("data", {})
            
            doc_info = {
                "type": f.type.lower(),
                "file_id": str(f.id),
                "siren": get_siren(content),
                "amount": get_ttc_amount(content),
                "date": content.get('date') or content.get('date_edition'),
                "raison_sociale": content.get('raison_sociale') or content.get('denomination'),
                "iban": str(content.get('iban', "")).replace(" ", "").upper(),
                "raw_content": content
            }
            docs_data.append(doc_info)
            source_files_meta.append({"file_id": str(f.id), "type": f.type})

    checks = []
    errors = []

    if not docs_data:
        return {"results": {"status_global": "error", "errors": ["Aucun fichier 'done' trouvé."]}}

    # --- RÈGLE 1 : CONSENSUS SIREN STRICT (TOUS les documents) ---
    # On identifie le SIREN majoritaire ou le premier trouvé
    sirens_found = [d['siren'] for d in docs_data if d['siren']]
    
    if not sirens_found:
        errors.append("Aucun identifiant (SIREN/SIRET) trouvé dans les documents.")
    else:
        # On définit une référence (ex: le premier trouvé)
        ref_siren = sirens_found[0]
        all_match = True
        
        for doc in docs_data:
            if doc['siren']:
                match = (doc['siren'] == ref_siren)
                if not match: all_match = False
                checks.append({
                    "code": f"SIREN_CHECK_{doc['type'].upper()}",
                    "label": f"Validation SIREN : {doc['type']}",
                    "status": "pass" if match else "fail",
                    "details": {"found": doc['siren'], "expected": ref_siren}
                })
        
        if not all_match:
            errors.append("Conflit d'identité : Les SIREN ne sont pas identiques sur tous les documents.")

    # --- RÈGLE 2 : COHÉRENCE RAISON SOCIALE ---
    names = [d for d in docs_data if d['raison_sociale']]
    if len(names) > 1:
        ref_name = clean_text(names[0]['raison_sociale'])
        for n in names[1:]:
            current_name = clean_text(n['raison_sociale'])
            # Vérification par inclusion pour gérer "SARL", "SAS", etc.
            is_ok = ref_name in current_name or current_name in ref_name
            checks.append({
                "code": f"NAME_CHECK_{n['type'].upper()}",
                "label": f"Raison Sociale : {n['type']}",
                "status": "pass" if is_ok else "warning",
                "details": {"found": n['raison_sociale'], "reference": names[0]['raison_sociale']}
            })

    # --- RÈGLE 3 : IBAN (RIB vs FACTURE) ---
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

    # --- RÈGLE 4 : MONTANTS (FACTURE vs DEVIS) ---
    devis = next((d for d in docs_data if "devis" in d['type']), None)
    if facture and devis:
        mt_f = facture['amount']
        mt_d = devis['amount']
        diff = abs(mt_f - mt_d) / mt_d if mt_d > 0 else (1.0 if mt_f > 0 else 0.0)
        checks.append({
            "code": "AMOUNT_CONSISTENCY",
            "label": "Montant TTC : Facture vs Devis",
            "status": "pass" if diff <= 0.05 else "warning",
            "details": {"diff_percent": round(diff * 100, 2), "invoice": mt_f, "quote": mt_d}
        })

    # --- RÈGLE 5 : CHRONOLOGIE ET VALIDITÉ ---
    if facture:
        f_date = facture['date']
        # vs Devis
        if devis and devis['date'] and f_date:
            checks.append({
                "code": "DATE_CHRONOLOGY",
                "label": "Chronologie : Devis avant Facture",
                "status": "pass" if devis['date'] <= f_date else "warning",
                "details": {"devis": devis['date'], "facture": f_date}
            })
        
        # vs Attestations (Doit être couverte par AU MOINS UNE attestation valide)
        attestations = [d for d in docs_data if "attestation" in d['type']]
        if attestations and f_date:
            valid_att = False
            for att in attestations:
                # On cherche la date de fin de validité
                end_date = att['raw_content'].get('date_validite') or att['raw_content'].get('periode_fin')
                if end_date and f_date <= end_date:
                    valid_att = True
                    break
            checks.append({
                "code": "LEGAL_VALIDITY",
                "label": "Attestation valide à la date facture",
                "status": "pass" if valid_att else "warning",
                "details": {"invoice_date": f_date}
            })

    # --- SYNTHÈSE FINALE ---
    status_global = "pass"
    if any(c["status"] == "fail" for c in checks): status_global = "fail"
    elif any(c["status"] == "warning" for c in checks): status_global = "warning"
    if errors: status_global = "fail"

    return {
        "meta": {
            "client_id": str(client_id),
            "generated_at": datetime.utcnow().isoformat(),
            "rule_set_version": "v3_consensus_strict",
            "source_files": source_files_meta
        },
        "results": {
            "status_global": status_global,
            "checks": checks,
            "errors": errors
        }
    }

# --- ROUTES FASTAPI ---

@router.post("", response_model=ConformityReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ConformityReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Vérification accès client
    client = await client_repo.get_client(db, payload.client_id)
    if not client or str(client.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Client not found")

    # Récupération des fichiers Silver
    files = await file_repo.list_files_for_client(db, payload.client_id)
    
    # Génération de l'analyse Gold par consensus
    gold_content = await generate_gold_analysis(payload.client_id, files)

    # Création du rapport
    return await report_repo.create_report(
        db,
        client_id=payload.client_id,
        gold_content=gold_content,
        processing_status="done" if gold_content["results"].get("status_global") != "error" else "error"
    )