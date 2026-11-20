# Périmètre de publication

Ce lot rassemble le guide, les analyses rédigées, les configurations et les outils nécessaires pour comprendre les essais Cozytouch. Il contient les sources et tests de la phase 2, les outils JTAG/OpenOCD et les paquets d’application CTAPP1. Les mentions « vérifié » se rapportent à un seul bridge et à la date indiquée.

Le lot exclut la notice Sauter, les exports de décompilation et de désassemblage, les corpus extraits des firmwares et les journaux bruts. Les tableaux de registres et les références courtes aux adresses ou offsets servent à expliquer les observations. Les images UBIFS, le noyau compilé, l’initramfs et les DTB compilés restent écartés. Leur éventuelle diffusion dépend de la vérification des licences et des obligations de fourniture des sources correspondantes.

Les preuves privées, l’historique Git et la configuration personnelle restent dans le dépôt d’origine. Les empreintes et identifiants de version consignés pendant les essais se rapportent aux artefacts de ces essais. Une expurgation peut changer l’empreinte du fichier publié.

## Marqueurs

| Marqueur | Signification |
| --- | --- |
| `<IP_HUB>` | Adresse du bridge |
| `<IP_ADMIN>` | Adresse d’un poste de maintenance |
| `<IP_COURTIER>` | Adresse du courtier MQTT |
| `<RESEAU_LOCAL>` | Réseau ou diffusion locale |
| `<MAC_HUB>` | Adresse matérielle |
| `<ID_PASSERELLE>` | Identifiant individuel de passerelle |
| `<NUMERO_BRIDGE>` | Numéro individuel imprimé sur le bridge |
| `<UTILISATEUR_MQTT>` | Compte du courtier |
| `<UTILISATEUR_ADMIN>` | Compte d’administration local |
| `<CLE_PUBLIQUE_ADMIN>` | Clé publique d’administration |
| `<EMPREINTE_CLE_HOTE>` | Empreinte de la clé d’hôte SSH |
| `<CHEMIN_LOCAL>` | Chemin ou nom d’hôte propre à l’installation |
| `<ADRESSE_APPAREIL_IO>` | Adresse individuelle io-homecontrol |
| `<PERSONNE>` | Identité personnelle |
| `<JETON>` | Paramètre signé ou jeton |

Les marqueurs représentent des valeurs à renseigner dans un environnement de reproduction. La recette historique de phase 2 dépend d’entrées de construction externes au lot, dont le CPIO de fusion. Les comptes et les contextes radio individuels se préparent sur l’installation de reproduction. Les adresses synthétiques des essais QEMU sont conservées.

## Licence

Le code est sous licence MIT et la documentation sous CC BY 4.0. Les exceptions (DTS dérivés du noyau Linux, configurations de projets tiers, extraits de firmwares constructeur) sont décrites dans le [README](README.md#licence). Les images binaires du système v4 ne sont pas publiées : le lot fournit les configurations et les recettes, et la reconstruction par un tiers n’a pas été testée.
