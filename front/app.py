import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
import time
import os
from services.auth_service import login as api_login, register as api_register, AuthServiceError

# --- 1. SETUP & THEME ---
st.set_page_config(page_title="KKthon", layout="wide")

# --- SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None


def login(email, password):
    try:
        data = api_login(email, password)
        st.session_state.logged_in = True
        st.session_state.access_token = data.get("access_token")
        st.session_state.refresh_token = data.get("refresh_token")
        user = data.get("user") or {}
        st.session_state.user_name = (
            user.get("user_metadata", {}).get("full_name")
            or user.get("email", "Utilisateur")
        )
        return True, None
    except AuthServiceError as e:
        return False, str(e)


def logout():
    st.session_state.logged_in = False
    st.session_state.user_name = ""
    st.session_state.access_token = None
    st.session_state.refresh_token = None

def load_css():
    css_file = os.path.join("assets", "style.css")
    if os.path.exists(css_path := css_file):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# --- 2. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("<h1 style='font-size: 24px;'>KKthon</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 14px;'>Plateforme intelligente d'analyse de documents.</p>", unsafe_allow_html=True)
    st.divider()

    if st.session_state.logged_in:
        st.caption(f"Connecté : {st.session_state.user_name}")
        selected = option_menu(
            menu_title=None,
            options=["Tableau de bord", "Analyser", "Liste clients", "Historique"],
            icons=["house-heart", "lightning-charge", "people", "archive"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "nav-link": {"font-size": "14px", "text-align": "left", "margin":"5px", "--hover-color": "#f1f5f9"},
                "nav-link-selected": {"background-color": "#0f172a", "color": "white"},
            }
        )
        st.divider()
        if st.button("Se déconnecter", use_container_width=True):
            logout()
            st.rerun()
    else:
        selected = option_menu(
            menu_title=None,
            options=["Connexion", "Inscription"],
            icons=["box-arrow-in-right", "person-plus"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "nav-link": {"font-size": "14px", "text-align": "left", "margin":"5px", "--hover-color": "#f1f5f9"},
                "nav-link-selected": {"background-color": "#0f172a", "color": "white"},
            }
        )

# --- 3. LOGIQUE DES PAGES ---

if selected == "Connexion":
    left, center, right = st.columns([1, 1.2, 1])

    with center:
        st.markdown("## Connexion")
        st.write("Accedez a votre espace pour suivre les documents et vos clients.")

        with st.form("login_form"):
            email = st.text_input("Adresse email", placeholder="exemple@kkthon.ai")
            password = st.text_input("Mot de passe", type="password", placeholder="Votre mot de passe")
            remember_me = st.checkbox("Se souvenir de moi")
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

elif selected == "Inscription":
    left, center, right = st.columns([1, 1.2, 1])

    with center:
        st.markdown("## Inscription")
        st.write("Creez un compte pour centraliser vos traitements OCR et votre portefeuille client.")

        with st.form("signup_form"):
            full_name = st.text_input("Nom complet", placeholder="Votre nom et prenom")
            company = st.text_input("Entreprise", placeholder="Nom de votre societe")
            email = st.text_input("Adresse email", placeholder="exemple@kkthon.ai")
            password = st.text_input("Mot de passe", type="password", placeholder="Choisissez un mot de passe")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password", placeholder="Retapez le mot de passe")
            accepted_terms = st.checkbox("J'accepte les conditions d'utilisation")
            submitted = st.form_submit_button("Creer mon compte")

        if submitted:
            if not full_name or not company or not email or not password or not confirm_password:
                st.error("Veuillez remplir tous les champs obligatoires.")
            elif password != confirm_password:
                st.error("Les mots de passe ne correspondent pas.")
            elif not accepted_terms:
                st.error("Vous devez accepter les conditions d'utilisation.")
            else:
                try:
                    api_register(email=email, password=password, full_name=full_name)
                    st.success("Compte créé avec succès. Vous pouvez maintenant vous connecter.")
                    st.info(f"Bienvenue {full_name}, votre espace {company} est prêt.")
                except AuthServiceError as e:
                    st.error(str(e))

elif selected in ("Tableau de bord", "Analyser", "Liste clients", "Historique") and not st.session_state.logged_in:
    st.warning("Veuillez vous connecter pour accéder à cette page.")
    st.stop()

elif selected == "Tableau de bord":
    st.markdown("## Bienvenue, voici vos statistiques")
    
    # KPIs avec colonnes aérées
    c1, c2, c3 = st.columns(3)
    c1.metric("Documents traités", "1,250", "↑ 12%")
    c2.metric("Précision OCR", "98.4%", "Stable")
    c3.metric("Temps gagné", "42h", "Ce mois")
    
    st.divider()
    
    # Graphique épuré
    st.subheader("Volume de documents extraits")
    df = pd.DataFrame({"Date": ["01/03", "05/03", "10/03", "15/03"], "Total": [120, 450, 300, 800]})
    fig = px.area(df, x="Date", y="Total", color_discrete_sequence=['#3b82f6'])
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

elif selected == "Analyser":
    st.markdown("## Centre de Traitement")
    st.info("Vous pouvez uploader plusieurs scans (Factures, Reçus, Contrats).")

    files = st.file_uploader("", type=['pdf', 'png', 'jpg'], accept_multiple_files=True)
    
    if files:
        st.markdown(f"**{len(files)} fichiers détectés**")
        if st.button("Lancer l'analyse intelligente"):
            progress_text = "Analyse des documents en cours..."
            my_bar = st.progress(0)
            
            for percent_complete in range(100):
                time.sleep(0.02)
                my_bar.progress(percent_complete + 1)
            
            st.success("Traitement terminé. Les données ont été injectées dans DuckDB.")
            st.balloons()

elif selected == "Liste clients":
    st.markdown("## Liste clients")
    st.write("Consultez votre portefeuille client, suivez leur statut et accedez rapidement aux informations utiles.")

    clients_df = pd.DataFrame({
        "Client ID": ["CL-001", "CL-002", "CL-003", "CL-004", "CL-005", "CL-006"],
        "Nom": ["Sophie Martin", "Karim Benali", "Emma Laurent", "Lucas Petit", "Ines Diallo", "Nathan Robert"],
        "Entreprise": ["Nova Conseil", "BatiPlus", "Azur Finance", "LogiTrans", "MediCare", "Urban Immo"],
        "Ville": ["Paris", "Lyon", "Marseille", "Toulouse", "Lille", "Nantes"],
        "Statut": ["Actif", "Actif", "En attente", "Actif", "Inactif", "En attente"],
        "Documents": [18, 9, 4, 27, 2, 7],
        "Dernier envoi": ["15/03/2026", "14/03/2026", "12/03/2026", "16/03/2026", "03/03/2026", "11/03/2026"]
    })

    c1, c2, c3 = st.columns(3)
    c1.metric("Clients total", f"{len(clients_df)}")
    c2.metric("Clients actifs", f"{(clients_df['Statut'] == 'Actif').sum()}")
    c3.metric("Documents suivis", f"{clients_df['Documents'].sum()}")

    st.divider()

    col_search, col_filter = st.columns([2, 1])
    search = col_search.text_input("Rechercher un client", placeholder="Nom, entreprise ou ville")
    status_filter = col_filter.selectbox("Filtrer par statut", ["Tous", "Actif", "En attente", "Inactif"])

    filtered_df = clients_df.copy()

    if search:
        search_value = search.lower()
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: search_value in " ".join(row.astype(str)).lower(),
                axis=1
            )
        ]

    if status_filter != "Tous":
        filtered_df = filtered_df[filtered_df["Statut"] == status_filter]

    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    st.subheader("Repartition des clients")
    status_counts = filtered_df["Statut"].value_counts().reset_index()
    status_counts.columns = ["Statut", "Total"]

    fig_clients = px.bar(
        status_counts,
        x="Statut",
        y="Total",
        color="Statut",
        color_discrete_map={
            "Actif": "#16a34a",
            "En attente": "#f59e0b",
            "Inactif": "#ef4444"
        }
    )
    fig_clients.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )
    st.plotly_chart(fig_clients, use_container_width=True)

elif selected == "Historique":
    st.markdown("## Explorateur de données")
    st.write("Consultez ici les données structurées extraites de vos documents.")
    
    # Simulation d'un tableau propre
    data = pd.DataFrame({
        "Date Import": ["16/03/2026", "15/03/2026", "14/03/2026"],
        "Nom du Fichier": ["Facture_EDF.pdf", "Note_Frais_01.jpg", "Contrat_Bail.pdf"],
        "Confiance": ["99%", "94%", "97%"],
        "Statut": ["✅ Validé", "✅ Validé", "⏳ À vérifier"]
    })
    st.dataframe(data, use_container_width=True, hide_index=True)
