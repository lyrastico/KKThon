# SUJET DU PROJET

Traitement automatique de documents administratifs

Vous allez développer en équipe une plateforme permettant :

i - l’upload multi-documents : pièces comptables sensibles

ii - Classification automatique : factures, devis, attestation, etc.

iii - Extraction des informations clés via OCR robustes : num SIREN, montants, ...

iv - Vérification intelligente et détection automatique d’incohérences entre ces différents documents (éventuellement documents frauduleux) : incohérence entre SIRET et sur attestation et celle sur facture, par exemple

v - Stockage suivant une logique Data Lake : raw zone, clean zone et curated zone ; Architecture Medallion : bronze, silver et gold

vi - Remplissage automatique de 2 front-ends ; applications métiers, par exemple : CRM et outil de conformité (éventuellement BDD fournisseur)

# STRUCTURE DU PROJET

amazon s3 bucket qui contient une archi data lake :
- raw
- bronze
- silver
- gold

orchestration airflow via astro (astronomer) :
- raw -> bronze (OCR)
- bronze -> silver (LLM)
- silver -> gold (Remonter des incohérences)

un OCR cloud (Document AI) qui va analyser les documents et les transformer en texte :
- raw -> text -> bronze (au format parquet ou json, à définir)

un LLM qui va analyser le texte et nous donner l'information de manière structurée :
- text -> json -> silver (au format parquet ou json, à définir)

1 frontend streamlit ou l'on s'authentifie en tant que gestionnaire de clients, un client regroupe plusieurs documents :
- factures
- devis
- KBIS
- etc...
le gestionnaire de clients vérifie que chacun des ses clients est bien conforme à la réglementation (RGPD, LGPD, etc...), il est aidé par notre outil qui croise les informations entre les différents documents.

le streamlit est appuyé par une DB Supabase pour : 
- les comptes gestionnaires de clients
- les clients
- les documents (accès à la silver & raw zone requise)
- les incohérences (accès à la gold & silver zone requise)