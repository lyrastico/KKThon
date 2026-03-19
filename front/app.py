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

# --- 1. SETUP & THEME ---
st.set_page_config(page_title="KKthon", layout="wide")


# Restauration de session au chargement.
# Le token est dans l'URL. (mauvaise manip pour un gros projet, mais fait l'affaire pour cet hakathon)
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
    # -- File detail view --
    if st.session_state.selected_file is not None:
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

    # -- Client detail view --
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
            pending = [f for f in files if f.processing_status != "done"]
            if pending:
                st.info(f"Traitement en cours... ({len(pending)} fichier(s) en attente)")
                st.progress((len(files) - len(pending)) / len(files))

            def _elapsed(created_at: str, updated_at: str, is_done: bool) -> str:
                """For done files: duration between creation and completion.
                For pending files: time elapsed since creation."""
                try:
                    created = datetime.fromisoformat(created_at)
                    end = datetime.fromisoformat(updated_at) if is_done else datetime.now(tz=created.tzinfo)
                    delta = int((end - created).total_seconds())
                    if delta < 60:
                        return f"{delta}s"
                    if delta < 3600:
                        return f"{delta // 60}m {delta % 60}s"
                    return f"{delta // 3600}h {(delta % 3600) // 60}m"
                except Exception:
                    return "-"

            hcols = st.columns([3, 1.5, 1.5, 1, 2, 1.5, 1, 1])
            for col, label in zip(hcols, ["Nom", "Type", "Format", "Statut", "Créé le", "Durée", "Ouvrir", "Supprimer"]):
                col.markdown(f"**{label}**")
            st.divider()

            for f in files:
                is_done = f.processing_status == "done"
                created_str = (
                    datetime.fromisoformat(f.created_at).strftime("%d/%m/%Y %H:%M")
                    if f.created_at else "-"
                )
                elapsed = _elapsed(f.created_at, f.updated_at, is_done)

                col_name, col_type, col_fmt, col_status, col_date, col_elapsed, col_open, col_del = st.columns([3, 1.5, 1.5, 1, 2, 1.5, 1, 1])
                col_name.write(f.original_filename)
                col_type.caption(f.type or "-")
                col_fmt.caption(f.file_format or "-")
                col_status.caption(f.processing_status)
                col_date.caption(created_str)
                col_elapsed.caption(elapsed)

                if is_done:
                    if col_open.button("Ouvrir", key=f"open_file_{f.file_id}"):
                        st.session_state.selected_file = str(f.file_id)
                        st.rerun()
                else:
                    col_open.caption("-")

                if col_del.button("Sup.", key=f"del_file_{f.file_id}"):
                    try:
                        delete_file(st.session_state.access_token, f.file_id)
                        st.success(f"Fichier {f.original_filename} supprimé.")
                        st.rerun()
                    except FileServiceError as e:
                        st.error(str(e))

            if pending:
                time.sleep(4)
                st.rerun()

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