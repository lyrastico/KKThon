## Dev1
#### J1 : test de streamlit
- interface complète mais mockée
#### J2 : streamlit avec supabase
interface utilisateur de gestionnaires de clients : 
- connexion (supabase)
- création de compte gestionnaire de clients (supabase)
- ajout de client (supabase)
- suppression de client (supabase)
- modification de client (supabase)
- visualisation de client (supabase)
- upload de documents par client (accès à la raw zone requise)
- classification des documents par client (accès à la silver zone requise)
- visualisation des documents par client (accès à la raw zone requise & silver zone requise)
- visualisation des incohérences par client (accès à la silver & gold zone requise)

#### J3 : à définir
#### J4 : à définir
## Dev2
#### J1 : backend (airflow) + cloud (document ai & LLM)
définir les solutions cloud à utiliser, en l'occurence :
- document ai (google cloud)
- Gemini flash 3.X (google cloud)
- Bucket S3 (amazon s3)
- airflow astro (astronomer)
- supabase
#### J2 : à définir
#### J3 : à définir
#### J4 : à définir
## Dev3
#### J1 : backend (supabase) conjointement avec le Dev1
#### J2 : à définir
#### J3 : à définir
#### J4 : à définir
## Dev4
#### J1 : création de données de test crédibles
- génération de documents types : factures, devis, KBIS, etc...
- avec de la variation dans les formats et la qualité des documents.
#### J2 : à définir
#### J3 : à définir
#### J4 : à définir
## Dev5
#### J1 : création des règles de conformité (RGPD, LGPD, etc...) entre silver & gold
- réfléchir à la manière de réconcilier les informations entre les différents documents, pour en extraire des types d'incohérences.
#### J2 : à définir
#### J3 : à définir
#### J4 : à définir