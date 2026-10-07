"""Compter les cas VSTest, puis refuser un résultat vert sans tests réussis."""

from pathlib import Path
import json
import os
import sys
import xml.etree.ElementTree as ET


def lire_statistiques(dossier):
    rapports = sorted(dossier.glob('*.trx'))
    if not rapports:
        raise ValueError('Aucun rapport de tests trouvé. Le nombre de cas est indisponible.')
    nombres = dict(total=0, executed=0, passed=0, failed=0, error=0, timeout=0, aborted=0)
    bilan_reussi = True
    for rapport in rapports:
        document = ET.parse(rapport).getroot()
        bilan = document.find('{*}ResultSummary')
        compteurs = document.find('{*}ResultSummary/{*}Counters')
        if bilan is None or compteurs is None:
            raise ValueError(f'Rapport incomplet : {rapport.name}.')
        bilan_reussi = bilan_reussi and bilan.get('outcome') in ('Completed', 'Passed')
        for cle in nombres:
            valeur = int(compteurs.get(cle, '0'))
            if valeur < 0:
                raise ValueError('Compteur de tests invalide.')
            nombres[cle] += valeur
    if not nombres['total'] >= nombres['executed'] >= nombres['passed'] + nombres['failed']:
        raise ValueError('Compteurs de tests incohérents.')
    nombres['skipped'] = nombres['total'] - nombres['executed']
    nombres['available'] = True
    return nombres, bilan_reussi


def valider(nombres, bilan_reussi):
    if nombres['executed'] == 0:
        raise ValueError('Aucun test réellement exécuté et réussi. Le lot reste à compléter.')
    if not bilan_reussi or nombres['passed'] != nombres['executed'] or any(nombres[k] for k in ('failed', 'error', 'timeout', 'aborted')):
        raise ValueError('Au moins un test exécuté n’a pas réussi.')
    return f"{nombres['passed']} test(s) réussi(s) sur {nombres['total']} cas découvert(s)."


def verifier(dossier):
    return valider(*lire_statistiques(dossier))


def publier_bilan(nombres):
    fichier_sortie = os.environ.get('GITHUB_OUTPUT')
    if fichier_sortie:
        with open(fichier_sortie, 'a', encoding='utf-8') as sortie:
            sortie.write('statistiques=' + json.dumps(nombres, separators=(',', ':')) + '\n')
    resume = os.environ.get('GITHUB_STEP_SUMMARY')
    if resume:
        with open(resume, 'a', encoding='utf-8') as sortie:
            if nombres['available']:
                sortie.write('| Cas détectés | Exécutés | Réussis | En échec | Non exécutés |\n')
                sortie.write('| ---: | ---: | ---: | ---: | ---: |\n')
                sortie.write(f"| {nombres['total']} | {nombres['executed']} | {nombres['passed']} | {nombres['failed']} | {nombres['skipped']} |\n")
            else:
                sortie.write('Nombre de tests indisponible : aucun rapport exploitable.\n')


if __name__ == '__main__':
    nombres = {'available': False}
    try:
        if len(sys.argv) != 2:
            raise ValueError('Usage : python3 verifier_resultats_tests.py dossier-des-rapports')
        nombres, bilan_reussi = lire_statistiques(Path(sys.argv[1]))
        message = valider(nombres, bilan_reussi)
    except (ValueError, OSError, ET.ParseError) as erreur:
        publier_bilan(nombres)
        print(f'Validation des tests : {erreur}', file=sys.stderr)
        sys.exit(1)
    publier_bilan(nombres)
    print(message)
