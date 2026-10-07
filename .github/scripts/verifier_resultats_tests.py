"""Refuser un résultat vert si aucun test n'a réellement réussi."""

from pathlib import Path
import os
import sys
import xml.etree.ElementTree as ET


def verifier(dossier):
    rapports = sorted(dossier.glob('*.trx'))
    if not rapports:
        raise ValueError('Aucun rapport de tests trouvé. Écrire et exécuter les tests du lot.')

    nombres = dict(total=0, executed=0, passed=0, failed=0, error=0, timeout=0, aborted=0)
    for rapport in rapports:
        document = ET.parse(rapport).getroot()
        bilan = document.find('{*}ResultSummary')
        compteurs = document.find('{*}ResultSummary/{*}Counters')
        if bilan is None or compteurs is None:
            raise ValueError(f'Rapport incomplet : {rapport.name}.')
        if bilan.get('outcome') not in ('Completed', 'Passed'):
            raise ValueError(f'Exécution non réussie : {rapport.name}.')
        for cle in nombres:
            valeur = int(compteurs.get(cle, '0'))
            if valeur < 0:
                raise ValueError('Compteur de tests invalide.')
            nombres[cle] += valeur

    if nombres['executed'] == 0 or nombres['passed'] == 0:
        raise ValueError('Aucun test réellement exécuté et réussi. Le lot reste à compléter.')
    if nombres['passed'] != nombres['executed'] or any(nombres[k] for k in ('failed', 'error', 'timeout', 'aborted')):
        raise ValueError('Au moins un test exécuté n’a pas réussi.')
    if nombres['total'] < nombres['executed']:
        raise ValueError('Compteurs de tests incohérents.')
    return f"{nombres['passed']} test(s) réussi(s) sur {nombres['total']} cas découvert(s)."


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('Usage : python3 verifier_resultats_tests.py dossier-des-rapports')
        message = verifier(Path(sys.argv[1]))
    except (ValueError, OSError, ET.ParseError) as erreur:
        print(f'Validation des tests : {erreur}', file=sys.stderr)
        sys.exit(1)
    print(message)
    resume = os.environ.get('GITHUB_STEP_SUMMARY')
    if resume:
        with open(resume, 'a', encoding='utf-8') as sortie:
            sortie.write(f'{message}\n')
