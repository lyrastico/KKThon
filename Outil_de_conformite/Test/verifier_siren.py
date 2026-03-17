#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification SIREN via API Gouv.fr
Extrait le SIREN d'un fichier et vérifie l'existence de l'entreprise
"""

import sys
import re
import requests
from pathlib import Path
import urllib3

# Désactiver les avertissements SSL (mode dev)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def extraire_siren(texte):
    """
    Extrait le numéro SIREN d'un texte
    
    Args:
        texte (str): Texte à analyser
        
    Returns:
        str: Numéro SIREN trouvé ou None
    """
    # Pattern SIREN: 9 chiffres consécutifs
    # Pattern SIRET: 14 chiffres (on prend les 9 premiers)
    patterns = [
        r'SIREN[:\s]*(\d{9})',
        r'SIRET[:\s]*(\d{14})',
        r'\b(\d{9})\b',
        r'\b(\d{14})\b'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texte, re.IGNORECASE)
        if match:
            numero = match.group(1)
            # Si c'est un SIRET (14 chiffres), prendre les 9 premiers
            if len(numero) == 14:
                return numero[:9]
            return numero
    
    return None


def verifier_siren_api(siren, mode_demo=False):
    """
    Vérifie l'existence d'une entreprise via l'API Gouv.fr
    
    Args:
        siren (str): Numéro SIREN à vérifier
        mode_demo (bool): Si True, retourne des données de démonstration
        
    Returns:
        dict: Informations de l'entreprise ou None
    """
    # Mode démonstration pour tester sans appeler l'API
    if mode_demo:
        print("ℹ️ Mode DEMO activé - Données simulées")
        return {
            'siren': siren,
            'nom_complet': 'URSSAF PROVENCE ALPES COTE D AZUR',
            'nom_raison_sociale': 'URSSAF PROVENCE ALPES COTE D AZUR',
            'siege': {
                'adresse': '56 RUE PARADIS',
                'code_postal': '13006',
                'commune': 'MARSEILLE'
            },
            'etat_administratif': 'A',
            'date_creation': '1967-01-01',
            'activite_principale': '84.11Z',
            'libelle_activite_principale': 'Administration publique générale',
            'tranche_effectif_salarie': '250 à 499 salariés',
            'categorie_juridique': 'Établissement public administratif'
        }
    
    url = f"https://recherche-entreprises.api.gouv.fr/search?q={siren}"
    
    # Headers recommandés par la documentation
    headers = {
        'User-Agent': 'Script-Verification-SIREN/1.0 (Hackathon-Formation)',
        'Accept': 'application/json'
    }
    
    try:
        # Désactiver la vérification SSL pour mode dev
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        
        # Gérer les codes d'erreur HTTP
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', '10')
            print(f"⚠️ Limite de requêtes API atteinte. Réessayez dans {retry_after} secondes.")
            return None
        elif response.status_code == 404:
            print("⚠️ API non disponible.")
            return None
        
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('total_results', 0) > 0:
            # Récupérer le premier résultat
            entreprise = data['results'][0]
            return {
                'siren': entreprise.get('siren'),
                'nom_complet': entreprise.get('nom_complet'),
                'nom_raison_sociale': entreprise.get('nom_raison_sociale'),
                'siege': entreprise.get('siege', {}),
                'etat_administratif': entreprise.get('etat_administratif'),
                'date_creation': entreprise.get('date_creation'),
                'activite_principale': entreprise.get('activite_principale'),
                'libelle_activite_principale': entreprise.get('libelle_activite_principale'),
                'tranche_effectif_salarie': entreprise.get('tranche_effectif_salarie'),
                'categorie_juridique': entreprise.get('nature_juridique')
            }
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la requête API: {e}")
        return None


def lire_fichier(chemin_fichier):
    """
    Lit le contenu d'un fichier
    
    Args:
        chemin_fichier (str): Chemin du fichier
        
    Returns:
        str: Contenu du fichier
    """
    try:
        with open(chemin_fichier, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Essayer avec un autre encodage
        try:
            with open(chemin_fichier, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Erreur de lecture du fichier: {e}")
            return None
    except Exception as e:
        print(f"❌ Erreur de lecture du fichier: {e}")
        return None


def afficher_resultat(siren, entreprise):
    """
    Affiche les résultats de la vérification
    
    Args:
        siren (str): Numéro SIREN recherché
        entreprise (dict): Informations de l'entreprise ou None
    """
    print("\n" + "="*60)
    print(f"VÉRIFICATION SIREN: {siren}")
    print("="*60)
    
    if entreprise:
        print("✅ ENTREPRISE TROUVÉE\n")
        
        print(f"Raison sociale: {entreprise.get('nom_raison_sociale', 'N/A')}")
        print(f"Nom complet: {entreprise.get('nom_complet', 'N/A')}")
        
        # Adresse du siège
        siege = entreprise.get('siege', {})
        if siege:
            adresse = siege.get('adresse', 'N/A')
            code_postal = siege.get('code_postal', '')
            commune = siege.get('commune', '')
            print(f"Adresse: {adresse}, {code_postal} {commune}")
        
        # État administratif
        etat = entreprise.get('etat_administratif', 'inconnu')
        if etat == 'A':
            print(f"Statut: ✅ ACTIF")
        elif etat == 'F':
            print(f"Statut: ❌ FERMÉ")
        else:
            print(f"Statut: {etat}")
        
        # Date de création
        date_creation = entreprise.get('date_creation', 'N/A')
        print(f"Date création: {date_creation}")
        
        # Activité
        activite = entreprise.get('activite_principale', '')
        libelle = entreprise.get('libelle_activite_principale', '')
        if activite:
            print(f"Activité: {libelle} ({activite})")
        
        # Effectif
        effectif = entreprise.get('tranche_effectif_salarie', '')
        if effectif:
            print(f"Tranche effectif: {effectif}")
        
    else:
        print("❌ ENTREPRISE NON TROUVÉE\n")
        print("Le numéro SIREN n'existe pas dans la base SIRENE.")
    
    print("="*60 + "\n")


def main():
    """Fonction principale"""
    if len(sys.argv) < 2:
        print("Usage: python verifier_siren.py <chemin_fichier> [--demo]")
        print("Exemple: python verifier_siren.py data/attestation_test.txt")
        print("         python verifier_siren.py data/attestation_test.txt --demo")
        sys.exit(1)
    
    chemin_fichier = sys.argv[1]
    mode_demo = '--demo' in sys.argv
    
    # Vérifier que le fichier existe
    if not Path(chemin_fichier).exists():
        print(f"❌ Erreur: Le fichier '{chemin_fichier}' n'existe pas.")
        sys.exit(1)
    
    print(f"📄 Lecture du fichier: {chemin_fichier}")
    
    # Lire le fichier
    contenu = lire_fichier(chemin_fichier)
    if not contenu:
        sys.exit(1)
    
    print(f"✅ Fichier lu: {len(contenu)} caractères")
    
    # Extraire le SIREN
    print("🔍 Recherche du numéro SIREN...")
    siren = extraire_siren(contenu)
    
    if not siren:
        print("❌ Aucun numéro SIREN trouvé dans le fichier.")
        sys.exit(1)
    
    print(f"✅ SIREN trouvé: {siren}")
    
    # Vérifier via l'API
    if mode_demo:
        print("🎭 Vérification en mode DEMO...")
    else:
        print("🌐 Vérification via l'API Gouv.fr...")
    
    entreprise = verifier_siren_api(siren, mode_demo=mode_demo)
    
    # Afficher le résultat
    afficher_resultat(siren, entreprise)


if __name__ == "__main__":
    main()
