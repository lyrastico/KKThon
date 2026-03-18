import re
from datetime import datetime

class DocumentValidator:
    def __init__(self, data):
        self.data = data
        self.report = []
        self.is_valid = True

    def _log_error(self, message):
        self.report.append(f"❌ {message}")
        self.is_valid = False

    def _log_success(self, message):
        self.report.append(f"✅ {message}")

    def check_identity(self):
        """Vérifie le SIREN sur tous les documents disponibles"""
        facture = self.data.get('facture', {})
        f_siret = facture.get('siret')
        
        if not f_siret:
            self._log_error("SIRET manquant sur la facture : Impossible de vérifier l'identité.")
            return

        f_siren = f_siret[:9]
        
        for doc_name in ['devis', 'kbis', 'attestation']:
            doc = self.data.get(doc_name)
            if doc:
                siren_doc = doc.get('siren')
                if siren_doc:
                    if f_siren == siren_doc:
                        self._log_success(f"SIREN identique : Facture & {doc_name.capitalize()}")
                    else:
                        self._log_error(f"SIREN différent : Facture ({f_siren}) vs {doc_name.capitalize()} ({siren_doc})")
                else:
                    self._log_error(f"SIREN absent du document {doc_name.capitalize()}")

    def check_banking(self):
        """Vérifie l'IBAN entre la facture et le RIB"""
        facture = self.data.get('facture', {})
        rib = self.data.get('rib', {})
        
        iban_f = facture.get('iban')
        iban_r = rib.get('iban')

        if iban_f and iban_r:
            clean_f = iban_f.replace(" ", "")
            clean_r = iban_r.replace(" ", "")
            if clean_f == clean_r:
                self._log_success("IBAN Facture conforme au RIB officiel")
            else:
                self._log_error(f"ALERTE FRAUDE : IBAN Facture ({clean_f}) != RIB ({clean_r})")
        else:
            self._log_error("IBAN manquant sur la facture ou le RIB : Vérification impossible.")

    def check_amounts(self):
        """Vérifie la cohérence des montants TTC (marge 5%)"""
        facture = self.data.get('facture', {})
        devis = self.data.get('devis', {})
        
        m_f = facture.get('montant_ttc')
        m_d = devis.get('montant_ttc')

        if m_f is not None and m_d is not None:
            if m_d == 0:
                self._log_error("Montant du devis est à zéro.")
                return
            diff = abs(m_f - m_d) / m_d
            if diff <= 0.05:
                self._log_success(f"Montant cohérent (Écart: {diff:.2%})")
            else:
                self._log_error(f"Écart de montant trop élevé : {diff:.2%}")
        else:
            self._log_error("Montant TTC absent sur la facture ou le devis.")

    def run_all_checks(self, scenario_name):
        print(f"\n--- TEST SCÉNARIO : {scenario_name} ---")
        self.report = []
        self.is_valid = True
        self.check_identity()
        self.check_banking()
        self.check_amounts()
        print("\n".join(self.report))
        return self.is_valid

# ==========================================================
# SCÉNARIOS DE TEST (Vérification de la robustesse)
# ==========================================================

cas_parfait = {
    "facture": {"siret": "12345678900012", "montant_ttc": 1000, "iban": "FR76123", "numero": "F01"},
    "devis": {"siren": "123456789", "montant_ttc": 1000},
    "kbis": {"siren": "123456789"},
    "attestation": {"siren": "123456789"},
    "rib": {"iban": "FR76123"}
}

cas_fraude_iban = {
    "facture": {"siret": "12345678900012", "montant_ttc": 1000, "iban": "FR99999", "numero": "F02"},
    "rib": {"iban": "FR76123"}
}

# Ce cas faisait planter l'ancien script à cause de l'iban manquant
cas_erreur_identite = {
    "facture": {"siret": "12345678900012", "numero": "F03"}, # Pas d'iban ici
    "kbis": {"siren": "999888777"},
    "rib": {"iban": "FR76123"}
}

if __name__ == "__main__":
    scenarios = [
        ("Dossier Conforme", cas_parfait),
        ("Suspicion de Fraude IBAN", cas_fraude_iban),
        ("Erreur d'Identité (Sans Crash)", cas_erreur_identite)
    ]

    for nom, data in scenarios:
        validator = DocumentValidator(data)
        validator.run_all_checks(nom)
        print("-" * 50)