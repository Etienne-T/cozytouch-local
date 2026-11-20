"""Write the acquisition summary and a manifest after successful verification."""
from pathlib import Path
import hashlib
import json
import sys

root = Path(sys.argv[1])
report = json.loads((root/'verification.json').read_text())
assert report['independent_read_sha256_verified'] and report['all_target_crc32_verified']
assert report['manifest_chunks_verified'] == 128
sha = report['sha256_A']
text = f'''# Sauvegarde NAND Cozytouch — 17 novembre 2026

Une image physique complète de la NAND est sauvegardée. Une **seconde lecture intégrale indépendante** est vérifiée par SHA-256 calculé directement sur le processeur du bridge : les 64 empreintes de lots concordent avec le fichier sauvegardé. Les CRC32 des 128 lots des deux passages concordent également. La seconde lecture produit des empreintes de vérification ; aucune deuxième image brute n'est reconstruite artificiellement.

Carte Atlantic 500090 / Overkiz Kizbox Mini, processeur AT91SAM9G25-CU, NAND Macronix MX30LF1G18AC-TI identifiée sur photo. Géométrie lue : 65536 pages de 2048 octets de données et 64 octets OOB, 1024 blocs de 64 pages.

**Image brute de référence : `nand-full-A-data-oob.raw`.** Les fichiers de diagnostic et les transferts rejetés conservés dans l'archive source ne sont pas des images de référence.

| Fichier | Taille | Contenu |
|---|---:|---|
| `nand-full-A-data-oob.raw` | 138412032 octets — 132 Mio | Première lecture, données et OOB entrelacés par page |
| `nand-data-128MiB.bin` | 134217728 octets — 128 Mio | Données extraites de A, sans OOB |
| `nand-oob-4MiB.bin` | 4194304 octets — 4 Mio | OOB extrait de A, dans l'ordre des pages |

SHA-256 de l'image brute complète :

`{sha}`

`verification.json` contient les contrôles de structure et les empreintes. `SHA256SUMS` permet de vérifier les fichiers livrés. `pass-A/manifest.jsonl` et `verification-B.jsonl` donnent les empreintes et CRC des deux lectures. L'archive `source-pi.tar.gz` conserve les acquisitions, plages transférées, indicateurs de pages effacées, journaux, configurations et sources du lecteur et du calcul SHA-256.

## Méthode et limites

Lecture JTAG avec un Raspberry Pi Model B Rev 2 et OpenOCD. Une routine ARM chargée en SRAM lit chaque page NAND, alimente le watchdog et calcule un CRC32. Les pages entièrement FF sont reconstituées après lecture effective et validation du CRC ; aucun bloc n'est sauté. Les transferts dont le CRC échoue sont rejetés et conservés comme diagnostics ; seuls les lots validés entrent dans les images finales.

Les OOB, ECC stockés et marqueurs de blocs sont préservés. Aucune correction ECC n'est appliquée à ces images brutes. Aucune commande d'effacement ou de programmation NAND n'a été envoyée. Le fonctionnement du bridge a été interrompu et sa RAM modifiée pour la lecture. Aucune restauration sur matériel n'a été testée.

Cette sauvegarde couvre la NAND du processeur Linux. Elle ne contient pas la flash interne du STM32 radio. Les images et archives restent privées.

Les détails techniques, branchements et incidents sont dans `ACQUISITION.md` et `jtag/README.md`.
'''
(root/'README.md').write_text(text, encoding='utf-8')
paths = [p for p in root.iterdir() if p.is_file() and p.name not in
         {'SHA256SUMS', 'copies-verifiees.json'}]
paths += [root/'pass-A/manifest.jsonl']
with (root/'SHA256SUMS').open('w', encoding='ascii', newline='\n') as out:
    for path in sorted(paths):
        digest = hashlib.sha256()
        with path.open('rb') as f:
            for buf in iter(lambda: f.read(1048576), b''):
                digest.update(buf)
        out.write(f'{digest.hexdigest()}  {path.relative_to(root).as_posix()}\n')
print('Summary and SHA256SUMS written after acquisition verification.')
