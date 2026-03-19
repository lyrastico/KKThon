"""
Barre de progression de la vérification des documents
"""

from __future__ import annotations

import math
import time
from datetime import datetime

import streamlit as st

from services.file_service import FileRecord, FileServiceError, get_file, delete_file

# Progress plan

STAGES = [
    # (duration_s, progress_target, label, micro_messages)
    (
        15,
        0.25,
        "Envoi vers le data lake",
        ["Connexion au stockage...", "Transfert du fichier...", "Vérification de l'intégrité..."],
    ),
    (
        12,
        0.50,
        "Reconnaissance optique (OCR)",
        ["Initialisation du moteur OCR...", "Extraction du texte...", "Nettoyage des données brutes..."],
    ),
    (
        15,
        0.80,
        "Analyse intelligente",
        ["Détection du type de document...", "Extraction des champs clés...", "Calcul du score de confiance..."],
    ),
    (
        None,  # indeterminate
        0.99,
        "Mise à disposition",
        ["Finalisation en cours...", "Dépend de la charge serveur...", "Presque prêt..."],
    ),
]

POLL_INTERVAL_FAST = 2.0   # seconds, stages 0-2
POLL_INTERVAL_SLOW = 5.0   # seconds, stage 3
TIMEOUT_WARNING_S  = 600   # 10 minutes


def _state_key(file_id: str) -> str:
    return f"fp_{file_id}"


def _init_state(file_id: str) -> None:
    key = _state_key(file_id)
    if key not in st.session_state:
        now = time.time()
        st.session_state[key] = {
            "start_ts":       now,
            "last_poll_ts":   now,
            "poll_attempts":  0,
            "backend_status": "pending",
            "stopped":        False,
        }


def _get_state(file_id: str) -> dict:
    return st.session_state[_state_key(file_id)]


def _simulated_progress(elapsed_s: float) -> tuple[float, int, str]:
    """Returns (progress 0.0-1.0, stage_index 0-3, micro_message)."""
    t = 0.0
    prev_p = 0.0
    for i, (duration, target_p, _, micros) in enumerate(STAGES):
        if duration is None:
            break
        if elapsed_s < t + duration:
            ratio = (elapsed_s - t) / duration
            p = prev_p + ratio * (target_p - prev_p)
            msg_idx = int(ratio * len(micros)) % len(micros)
            return min(p, target_p), i, micros[msg_idx]
        t += duration
        prev_p = target_p

    # Stage 3: asymptotic 90% → 99%
    extra = elapsed_s - t
    p = 0.90 + 0.09 * (1 - math.exp(-extra / 30))
    stage3_micros = STAGES[3][3]
    msg_idx = int(extra / 5) % len(stage3_micros)
    return min(p, 0.99), 3, stage3_micros[msg_idx]


def _poll_backend(file_id: str, access_token: str) -> str:
    """Calls the backend and updates state. Returns the new status."""
    state = _get_state(file_id)
    try:
        record: FileRecord = get_file(access_token, file_id)
        state["backend_status"] = record.processing_status
    except FileServiceError:
        pass  # keep previous status on transient errors
    state["last_poll_ts"] = time.time()
    state["poll_attempts"] += 1
    return state["backend_status"]


def _should_poll(file_id: str, stage_idx: int) -> bool:
    state = _get_state(file_id)
    interval = POLL_INTERVAL_SLOW if stage_idx == 3 else POLL_INTERVAL_FAST
    return (time.time() - state["last_poll_ts"]) >= interval


def _stepper_html(current_stage: int, backend_status: str) -> str:
    """Renders a simple inline stepper."""
    icons = {
        "todo":        ("⬜", "#94a3b8"),
        "in_progress": ("🔵", "#3b82f6"),
        "done_step":   ("✅", "#22c55e"),
        "error":       ("❌", "#ef4444"),
    }

    items = []
    for i, (_, _, label, _) in enumerate(STAGES):
        if backend_status == "failed" and i == current_stage:
            state = "error"
        elif i < current_stage or backend_status == "done":
            state = "done_step"
        elif i == current_stage:
            state = "in_progress"
        else:
            state = "todo"

        icon, color = icons[state]
        dur = f"~{STAGES[i][0]}s" if STAGES[i][0] else "variable"
        items.append(
            f'<div style="display:flex;align-items:center;gap:6px;color:{color};font-size:13px;">'
            f'{icon} <span>{label}</span>'
            f'<span style="color:#94a3b8;font-size:11px;">({dur})</span>'
            f'</div>'
        )

    connector = '<div style="width:2px;height:10px;background:#e2e8f0;margin-left:9px;"></div>'
    return '<div style="display:flex;flex-direction:column;gap:2px;">' + connector.join(items) + '</div>'


# Public API

def render_pending_file(file_id: str, filename: str, access_token: str) -> bool:
    """
    Renders the animated progress widget for one pending file.
    Returns True if processing is still active (caller should schedule a rerun).
    Returns False if done, failed, or user stopped.
    """
    _init_state(file_id)
    state = _get_state(file_id)

    if state["stopped"]:
        st.caption(f"{filename} — suivi arrêté.")
        return False

    elapsed = time.time() - state["start_ts"]
    progress, stage_idx, micro_msg = _simulated_progress(elapsed)
    backend_status = state["backend_status"]

    # Poll backend
    if _should_poll(file_id, stage_idx):
        backend_status = _poll_backend(file_id, access_token)

    with st.container():
        st.markdown(f"**{filename}**")

        if backend_status == "failed":
            st.error("Le traitement a échoué.")
            col_retry, col_support = st.columns([1, 1])
            col_retry.button("Réessayer", key=f"retry_{file_id}")
            col_support.button("Contacter le support", key=f"support_{file_id}")
            return False

        if backend_status == "done":
            st.progress(1.0)
            st.success("Traitement terminé. Rechargement...")
            return False

        # Still processing
        if elapsed > TIMEOUT_WARNING_S:
            st.warning("Toujours en cours — cela peut prendre plus de temps que prévu.")

        st.progress(progress)
        st.caption(micro_msg)

        # Stepper
        st.markdown(
            _stepper_html(stage_idx, backend_status),
            unsafe_allow_html=True,
        )

        col_detail, col_stop = st.columns([4, 1])
        with col_detail:
            with st.expander("Détails du suivi", expanded=False):
                st.caption(f"Durée : {elapsed:.0f}s")
                st.caption(f"Polls effectués : {state['poll_attempts']}")
                st.caption(f"Dernier statut backend : {backend_status}")
                st.caption(f"Progression simulée : {progress * 100:.1f}%")
        with col_stop:
            if st.button("Arrêter", key=f"stop_{file_id}"):
                state["stopped"] = True
                st.rerun()

    return True  # still active


def render_files_section(files: list[FileRecord], access_token: str) -> None:
    """
    Affiche la section complète du document pour un client :
    - Les fichiers actifs (en attente/en cours de traitement) bénéficient d'un widget de progression animé.
    - Les fichiers terminés sont listés dans un tableau récapitulatif.
    - Gère la boucle de réexécution de l'interrogation globale.
    """
    pending = [f for f in files if f.processing_status not in ("done", "failed")]
    done    = [f for f in files if f.processing_status == "done"]
    failed  = [f for f in files if f.processing_status == "failed"]

    any_active = False

    if pending:
        st.subheader(f"En cours de traitement ({len(pending)})")
        for f in pending:
            still_active = render_pending_file(str(f.file_id), f.original_filename, access_token)
            any_active = any_active or still_active
            st.divider()

    if failed:
        st.subheader(f"Echecs ({len(failed)})")
        for f in failed:
            st.error(f"{f.original_filename} — traitement échoué.")

    if done:
        st.subheader(f"Documents disponibles ({len(done)})")
        _render_done_table(done, access_token)

    if any_active:
        time.sleep(0.4)
        st.rerun()


def _render_done_table(files: list[FileRecord], access_token: str) -> None:
    """Compact table for processed files."""

    def _elapsed_done(created_at: str, updated_at: str) -> str:
        try:
            delta = int(
                (datetime.fromisoformat(updated_at) - datetime.fromisoformat(created_at))
                .total_seconds()
            )
            if delta < 60:
                return f"{delta}s"
            if delta < 3600:
                return f"{delta // 60}m {delta % 60}s"
            return f"{delta // 3600}h {(delta % 3600) // 60}m"
        except Exception:
            return "-"

    hcols = st.columns([3, 1.5, 1.5, 2, 1.5, 1, 1])
    for col, label in zip(hcols, ["Nom", "Type", "Format", "Créé le", "Durée", "Ouvrir", "Supprimer"]):
        col.markdown(f"**{label}**")
    st.divider()

    for f in files:
        created_str = (
            datetime.fromisoformat(f.created_at).strftime("%d/%m/%Y %H:%M")
            if f.created_at else "-"
        )
        elapsed = _elapsed_done(f.created_at, f.updated_at)

        c_name, c_type, c_fmt, c_date, c_elapsed, c_open, c_del = st.columns([3, 1.5, 1.5, 2, 1.5, 0.5, 0.5])
        c_name.write(f.original_filename)
        c_type.caption(f.type or "-")
        c_fmt.caption(f.file_format or "-")
        c_date.caption(created_str)
        c_elapsed.caption(elapsed)
        if c_open.button("👁", key=f"open_done_{f.file_id}"):
            st.session_state.selected_file = str(f.file_id)
            st.rerun()
        if c_del.button("🗑", key=f"del_done_{f.file_id}"):
            try:
                delete_file(access_token, f.file_id)
                st.rerun()
            except FileServiceError as e:
                st.error(str(e))