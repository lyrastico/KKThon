from datetime import datetime, timezone
import time

import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
import os
from services.client_service import ClientServiceError, create_client, delete_client, list_clients
from services.auth_service import login as api_login, register as api_register, AuthServiceError
from services.file_service import FileServiceError, list_files, upload_file, delete_file, get_file
from components.file_progress import render_files_section
from services.conformity_report_service import (
    ConformityReportServiceError,
    create_report as api_create_report,
    list_reports as api_list_reports,
    delete_report as api_delete_report,
    get_report as api_get_report,
)

# --- 1. SETUP & THEME ---
st.set_page_config(page_title="KKthon", layout="wide")


# Session restoration from URL token.
if "logged_in" not in st.session_state:
    session_token = st.query_params.get("session_token")
    if session_token:
        st.session_state.logged_in = True
        st.session_state.access_token = session_token
        st.session_state.user_name = st.query_params.get("user_name", "Utilisateur")
    else:
        st.session_state.logged_in = False
        st.session_state.access_token = None
        st.session_state.user_name = ""

if "selected_client" not in st.session_state:
    st.session_state.selected_client = None

if "selected_file" not in st.session_state:
    st.session_state.selected_file = None

if "selected_report" not in st.session_state:
    st.session_state.selected_report = None


def login(email: str, password: str) -> tuple[bool, str | None]:
    try:
        data = api_login(email, password)
        access_token = data.get("access_token")
        user = data.get("user") or {}
        user_name = (
            user.get("user_metadata", {}).get("full_name")
            or user.get("email", "Utilisateur")
        )
        st.session_state.logged_in = True
        st.session_state.access_token = access_token
        st.session_state.user_name = user_name
        st.query_params["session_token"] = access_token
        st.query_params["user_name"] = user_name
        return True, None
    except AuthServiceError as e:
        return False, str(e)


def logout():
    st.session_state.logged_in = False
    st.session_state.access_token = None
    st.session_state.user_name = ""
    st.session_state.selected_client = None
    st.session_state.selected_file = None
    st.session_state.selected_report = None
    st.query_params.clear()


def load_css():
    path = os.path.join("assets", "style.css")
    if os.path.exists(path):
        with open(path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


# --- 2. SIDEBAR NAVIGATION ---
MENU_STYLES = {
    "container": {"padding": "0!important", "background-color": "transparent"},
    "nav-link": {"font-size": "14px", "text-align": "left", "margin": "5px", "--hover-color": "#f1f5f9"},
    "nav-link-selected": {"background-color": "#0f172a", "color": "white"},
}

# Barre latérale
with st.sidebar:
    st.markdown("<h1 style='font-size: 24px;'>KKthon</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px;'>Plateforme intelligente d'analyse de documents.</p>", unsafe_allow_html=True)
    st.divider()

    if st.session_state.logged_in:
        st.caption(f"Connecté : {st.session_state.user_name}")
        page = option_menu(
            menu_title=None,
            options=["Tableau de bord", "Liste clients", "Historique"],
            icons=["house", "people", "archive"],
            menu_icon="cast",
            default_index=0,
            styles=MENU_STYLES,
        )
        st.divider()
        if st.button("Se déconnecter", use_container_width=True):
            logout()
            st.rerun()
    else:
        page = option_menu(
            menu_title=None,
            options=["Connexion", "Inscription"],
            icons=["box-arrow-in-right", "person-plus"],
            menu_icon="cast",
            default_index=0,
            styles=MENU_STYLES,
        )

# --- 3. PAGES ---

if page == "Connexion":
    left, center, right = st.columns([1, 1.2, 1])
    with center:
        st.markdown("## Connexion")
        st.write("Accédez à votre espace pour suivre les documents et vos clients.")
        with st.form("login_form"):
            email = st.text_input("Adresse email", placeholder="exemple@kkthon.ai")
            password = st.text_input("Mot de passe", type="password", placeholder="Votre mot de passe")
            st.checkbox("Se souvenir de moi")
            submitted = st.form_submit_button("Se connecter")
        if submitted:
            if not email or not password:
                st.error("Veuillez renseigner votre email et votre mot de passe.")
            else:
                ok, err = login(email, password)
                if ok:
                    st.rerun()
                else:
                    st.error(err)
        st.caption("Pas encore de compte ? Rendez-vous sur la page Inscription.")

elif page == "Inscription":
    left, center, right = st.columns([1, 1.2, 1])

    with center:
        st.markdown("## Inscription")
        st.write("Créez un compte pour centraliser vos traitements OCR et votre portefeuille client.")

        with st.form("signup_form"):
            full_name = st.text_input("Nom complet", placeholder="Votre nom et prénom")
            email = st.text_input("Adresse email", placeholder="exemple@kkthon.ai")
            password = st.text_input("Mot de passe", type="password", placeholder="Choisissez un mot de passe")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password", placeholder="Retapez le mot de passe")
            accepted_terms = st.checkbox("J'accepte les conditions d'utilisation")
            submitted = st.form_submit_button("Créer mon compte")

        if submitted:
            if not full_name or not email or not password or not confirm_password:
                st.error("Veuillez remplir tous les champs obligatoires.")
            elif password != confirm_password:
                st.error("Les mots de passe ne correspondent pas.")
            elif not accepted_terms:
                st.error("Vous devez accepter les conditions d'utilisation.")
            else:
                try:
                    api_register(email=email, password=password, full_name=full_name)
                    ok, err = login(email, password)
                    if ok:
                        st.rerun()
                    else:
                        st.error(err)
                except AuthServiceError as e:
                    st.error(str(e))
# Redirection si non connecté
elif page in ("Tableau de bord", "Liste clients", "Historique") and not st.session_state.logged_in:
    st.warning("Veuillez vous connecter pour accéder à cette page.")
    st.stop()

elif page == "Tableau de bord":
    st.markdown(f"## Bienvenue {st.session_state.user_name}, voici vos statistiques")
    col1, col2, col3 = st.columns(3)
    col1.metric("Documents traités", "1 250", "↑ 12%")
    col2.metric("Précision OCR", "98,4%", "Stable")
    col3.metric("Temps gagné", "42h", "Ce mois")
    st.divider()
    st.subheader("Volume de documents extraits")
    df = pd.DataFrame({"Date": ["01/03", "05/03", "10/03", "15/03"], "Total": [120, 450, 300, 800]})
    fig = px.area(df, x="Date", y="Total", color_discrete_sequence=["#3b82f6"])
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

elif page == "Liste clients":
    # -- Vue détaillée File --
    if st.session_state.selected_report is not None:
        if st.button("← Retour aux documents"):
            st.session_state.selected_report = None
            st.rerun()

        try:
            report = api_get_report(st.session_state.access_token, st.session_state.selected_report)
        except ConformityReportServiceError as e:
            st.error(str(e))
            st.stop()

        gc = report.gold_content or {}
        meta = gc.get("meta", {})
        results = gc.get("results", {})
        checks = results.get("checks", [])
        missing = results.get("missing_documents", [])
        errors = results.get("errors", [])
        status_global = results.get("status_global", "unknown")
        source_files = meta.get("source_files", [])

        generated_at = meta.get("generated_at", "")
        try:
            generated_at = datetime.fromisoformat(generated_at).strftime("%d/%m/%Y à %H:%M")
        except Exception:
            pass

        # --- Header ---
        st.markdown("## Rapport de conformité")
        st.caption(
            f"Généré le {generated_at}  ·  "
            f"Version des règles : {meta.get('rule_set_version', '-')}  ·  "
            f"{len(source_files)} fichier(s) analysé(s)"
        )
        st.divider()

        # --- Global verdict (prominent) ---
        _VERDICT = {
            "pass":    ("🟢", "Conforme",      "success", "Tous les contrôles automatiques ont été passés avec succès."),
            "fail":    ("🔴", "Non conforme",   "error",   "Un ou plusieurs contrôles ont échoué. Consultez le détail ci-dessous."),
            "unknown": ("⚪", "Indéterminé",    "warning", "Aucun fichier traité disponible pour générer une analyse."),
        }
        v_icon, v_label, v_type, v_desc = _VERDICT.get(status_global, _VERDICT["unknown"])

        col_verdict, col_counts = st.columns([2, 1])
        with col_verdict:
            getattr(st, v_type)(f"**{v_icon} {v_label}** — {v_desc}")
        with col_counts:
            n_pass    = sum(1 for c in checks if c["status"] == "pass")
            n_warning = sum(1 for c in checks if c["status"] == "warning")
            n_fail    = sum(1 for c in checks if c["status"] == "fail")
            st.markdown(
                f"✅ **{n_pass}** conforme(s) &nbsp;&nbsp; "
                f"⚠️ **{n_warning}** avertissement(s) &nbsp;&nbsp; "
                f"❌ **{n_fail}** échec(s)",
                unsafe_allow_html=True,
            )

        st.divider()

        # --- Checks detail ---
        if checks:
            st.subheader("Détail des contrôles")
            st.caption("Chaque ligne représente une règle métier appliquée automatiquement sur vos documents.")

            _ICON  = {"pass": "✅", "fail": "❌", "warning": "⚠️"}
            _LABEL = {"pass": "OK", "fail": "Échec", "warning": "Attention"}

            for c in checks:
                icon  = _ICON.get(c["status"], "-")
                label = _LABEL.get(c["status"], c["status"])
                details = c.get("details", {})

                with st.container():
                    col_icon, col_body, col_detail = st.columns([0.4, 4, 3])
                    col_icon.markdown(f"## {icon}")
                    with col_body:
                        st.markdown(f"**{c['label']}**")
                        st.caption(f"Code : `{c['code']}`  ·  Résultat : **{label}**")
                    with col_detail:
                        if details:
                            for k, v in details.items():
                                st.caption(f"{k.replace('_', ' ').capitalize()} : **{v}**")
                    st.divider()

        # --- Documents manquants ---
        if missing:
            st.subheader("Documents manquants")
            st.caption("Ces types de documents n'ont pas été fournis. Certains contrôles n'ont pas pu être effectués.")
            cols = st.columns(len(missing))
            for col, doc in zip(cols, missing):
                col.warning(f"📄 {doc}")
            st.divider()

        # --- Erreurs d'analyses ---
        if errors:
            st.subheader("Problèmes détectés lors de l'analyse")
            st.caption("Ces erreurs techniques ont empêché certains contrôles de s'exécuter.")
            for err in errors:
                st.error(err)
            st.divider()

        # --- Source files ---
        if source_files:
            with st.expander(f"Fichiers utilisés pour ce rapport ({len(source_files)})", expanded=False):
                st.caption("Liste des fichiers dont le traitement était terminé au moment de la génération.")
                for sf in source_files:
                    st.markdown(
                        f"- **Type** : {sf.get('type') or 'inconnu'}  ·  "
                        f"**ID** : `{sf.get('file_id', '-')}`  ·  "
                        f"**S3** : `{sf.get('s3_raw_path', '-')}`"
                    )

    # -- File detail view --
    elif st.session_state.selected_file is not None:
        if st.button("← Retour aux documents"):
            st.session_state.selected_file = None
            st.rerun()

        try:
            f = get_file(st.session_state.access_token, st.session_state.selected_file)
        except FileServiceError as e:
            st.error(str(e))
            st.stop()

        st.markdown(f"## {f.original_filename}")
        st.caption(f"ID : {f.file_id}")
        st.divider()

        col_meta1, col_meta2, col_meta3 = st.columns(3)
        col_meta1.metric("Format", f.file_format or "-")
        col_meta2.metric("Type", f.type or "-")
        col_meta3.metric("Statut", f.processing_status)

        sc = f.silver_content
        if not sc:
            st.info("Aucun contenu extrait disponible.")
        else:
            result = sc.get("result", {})
            source = sc.get("source", {})
            processing = sc.get("processing", {})

            st.divider()

            st.subheader("Données extraites")
            data = result.get("data", {})
            conf = result.get("confidence_score")
            doc_type = result.get("document_detected", "-")

            col_conf, col_doc = st.columns(2)
            col_conf.metric("Score de confiance", f"{conf * 100:.1f} %" if conf is not None else "-")
            col_doc.metric("Type de document détecté", doc_type)

            if data:
                st.markdown("**Champs extraits**")
                rows = [{"Champ": k.replace("_", " ").capitalize(), "Valeur": v} for k, v in data.items()]
                st.table(pd.DataFrame(rows).set_index("Champ"))
            else:
                st.info("Aucun champ extrait.")

            st.divider()

            col_src, col_proc = st.columns(2)
            with col_src:
                st.subheader("Source")
                st.caption(f"Bucket : {source.get('bucket', '-')}")
                st.caption(f"Clé S3 : {source.get('key', '-')}")
                st.caption(f"MIME : {source.get('mime_type', '-')}")
            with col_proc:
                st.subheader("Traitement")
                st.caption(f"Modèle : {processing.get('model', '-')}")
                processed_at = processing.get("processed_at")
                if processed_at:
                    try:
                        processed_at = datetime.fromisoformat(processed_at.replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        pass
                st.caption(f"Traité le : {processed_at or '-'}")

    # -- Vue detaillée Client --
    elif st.session_state.selected_client is not None:
        client_id, client_name = st.session_state.selected_client

        if st.button("← Retour à la liste"):
            st.session_state.selected_client = None
            st.rerun()

        st.markdown(f"## {client_name}")
        st.divider()

        # File upload section
        st.subheader("Ajouter des documents")
        uploaded_files = st.file_uploader(
            "Sélectionnez un ou plusieurs fichiers",
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="client_file_uploader",
        )
        if uploaded_files:
            if st.button("Envoyer les fichiers"):
                errors = []
                successes = 0
                for uf in uploaded_files:
                    try:
                        upload_file(
                            st.session_state.access_token,
                            client_id,
                            uf.read(),
                            uf.name,
                            uf.type or "application/octet-stream",
                        )
                        successes += 1
                    except FileServiceError as e:
                        errors.append(f"{uf.name} : {e}")
                if successes:
                    st.success(f"{successes} fichier(s) envoyé(s) avec succès.")
                for err in errors:
                    st.error(err)
                st.rerun()

        st.divider()

        # File list section
        st.subheader("Documents du client")
        try:
            files = list_files(st.session_state.access_token, client_id)
        except FileServiceError as e:
            st.error(str(e))
            files = []

        if not files:
            st.info("Aucun document pour ce client.")
        else:
            render_files_section(files, st.session_state.access_token)

        st.divider()

        # Conformity report section
        st.subheader("Rapport de conformité")

        try:
            reports = api_list_reports(st.session_state.access_token, client_id)
        except ConformityReportServiceError as e:
            st.error(str(e))
            reports = []

        if st.button("Générer un nouveau rapport"):
            with st.spinner("Analyse en cours..."):
                try:
                    new_report = api_create_report(st.session_state.access_token, client_id)
                    st.success("Rapport généré.")
                    st.session_state.selected_report = str(new_report.report_id)
                    st.rerun()
                except ConformityReportServiceError as e:
                    st.error(str(e))

        if reports:
            _status_icon = {"pass": "🟢", "fail": "🔴", "unknown": "⚪", "error": "🔴", "done": "🟢"}
            for r in sorted(reports, key=lambda x: x.created_at, reverse=True):
                status_global = (r.gold_content or {}).get("results", {}).get("status_global", r.processing_status)
                icon = _status_icon.get(status_global, "⚪")
                try:
                    created = datetime.fromisoformat(r.created_at).strftime("%d/%m/%Y %H:%M")
                except Exception:
                    created = r.created_at

                col_date, col_status, col_open, col_del = st.columns([3, 2, 0.5, 0.5])
                col_date.write(created)
                col_status.caption(f"{icon} {status_global}")
                if col_open.button("👁", key=f"open_report_{r.report_id}", help="Voir le rapport"):
                    st.session_state.selected_report = str(r.report_id)
                    st.rerun()
                if col_del.button("🗑", key=f"del_report_{r.report_id}", help="Supprimer le rapport"):
                    try:
                        api_delete_report(st.session_state.access_token, r.report_id)
                        st.rerun()
                    except ConformityReportServiceError as e:
                        st.error(str(e))
        else:
            st.info("Aucun rapport généré pour ce client.")

    # -- Client list view --
    else:
        st.markdown("## Liste clients")
        st.write("Cliquez sur un client pour accéder à ses documents.")

        try:
            clients = list_clients(st.session_state.access_token)
        except ClientServiceError as e:
            st.error(str(e))
            clients = []

        clients_df = pd.DataFrame([
            {
                "client_id": str(c.client_id),
                "Nom": c.client_name,
                "Date de création": datetime.fromisoformat(c.created_at).strftime("%d/%m/%Y") if c.created_at else "",
            }
            for c in clients
        ])

        col1, col2 = st.columns(2)
        col1.metric("Clients total", len(clients))
        col2.metric("Documents suivis", sum(getattr(c, "documents_count", 0) for c in clients))
        st.divider()

        with st.expander("Ajouter un client", expanded=False):
            with st.form("add_client_form"):
                new_name = st.text_input("Nom du client", placeholder="Nom ou raison sociale")
                submitted = st.form_submit_button("Créer")
            if submitted:
                if not new_name.strip():
                    st.error("Le nom du client est obligatoire.")
                else:
                    try:
                        create_client(st.session_state.access_token, new_name.strip())
                        st.success("Client créé avec succès.")
                        st.rerun()
                    except ClientServiceError as e:
                        st.error(str(e))

        st.divider()
        search = st.text_input("Rechercher un client", placeholder="Nom")
        filtered_df = (
            clients_df[clients_df["Nom"].str.contains(search, case=False, na=False)]
            if search and not clients_df.empty
            else clients_df
        )

        if filtered_df.empty:
            st.info("Aucun client trouvé.")
        else:
            for _, row in filtered_df.iterrows():
                col_name, col_date, col_open, col_del = st.columns([3, 2, 1, 1])
                col_name.write(row["Nom"])
                col_date.caption(row["Date de création"])
                if col_open.button("Ouvrir", key=f"open_{row['client_id']}"):
                    st.session_state.selected_client = (row["client_id"], row["Nom"])
                    st.rerun()
                if col_del.button("Supprimer", key=f"del_{row['client_id']}"):
                    try:
                        delete_client(st.session_state.access_token, row["client_id"])
                        st.success(f"Client {row['Nom']} supprimé.")
                        st.rerun()
                    except ClientServiceError as e:
                        st.error(str(e))

elif page == "Historique":
    st.markdown("## Explorateur de données")
    st.write("Consultez ici les données structurées extraites de vos documents.")
    df_history = pd.DataFrame({
        "Date Import": ["16/03/2026", "15/03/2026", "14/03/2026"],
        "Nom du Fichier": ["Facture_EDF.pdf", "Note_Frais_01.jpg", "Contrat_Bail.pdf"],
        "Confiance": ["99%", "94%", "97%"],
        "Statut": ["Validé", "Validé", "A vérifier"],
    })
    st.dataframe(df_history, use_container_width=True, hide_index=True)