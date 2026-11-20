# Diagnostic des bornes de consigne CETHI — résultat du 20 novembre 2026, vers 13 h 15 (heure de Paris)

Essai autorisé par <PERSONNE> (« parfait allons y »). Procédure : `PROCEDURE.md`, avec le script `phase2/diag/bornes-diag.lua` (SHA-256 `81dfda97…`, vérifié sur le hub).

## Déroulé

1. **État de départ :** v4 `v-1b3e4c30f96c` en mode `current`, sain, sans `next` ni `trying`.
2. **Arrêt du service :** fils du superviseur arrêté par TERM (PID 65), arrêt confirmé.
3. **Diagnostic :** code 0, `DIAG_DONE restored=true`. Sorties : `bornes-stdout.txt` et `bornes-diag.txt`, contexte masqué.
4. **Redémarrage :** `ct-update reboot`, puis `HEALTHY=yes` à 21 secondes. Nouvel identifiant de démarrage. Mode `current`, toujours sur v4.

## Réponses du chauffe-eau

Chaque demande a reçu une seule trame `0x010d`, en 65 à 82 ms, avec le statut 05 (DONE) et le détail 00. Aucune trame tardive ou en double.

| Demande | Longueur | Octets 11 et suivants | Valeur |
|---|---|---|---|
| Type 3 (MAIN_INFO) | 28 | `00 96 00 04 05 00 c8 00 c8 00 …` | réponse habituelle |
| Type 7 (borne haute) | 20 | `00 8e 00 04 05 00 82 eb 00 00` | 33515 centièmes de kelvin, soit **62,00 °C** |
| Type 6 (borne basse) | 20 | `00 8e 00 04 05 00 72 83 00 00` | 29315 centièmes de kelvin, soit **20,00 °C** |
| Type 7 (borne haute, seconde demande) | 20 | identique à la première | 62,00 °C |
| Type 3 (MAIN_INFO, seconde demande) | 28 | identique à la première | — |

## Conclusions

- **Le format prévu par la recherche est confirmé :** réponse de 20 octets, valeur sur 16 bits gros-boutiste aux octets 17–18, en centièmes de kelvin, FPI à 0.
- **Consigne actuelle :** `target_raw` = 51200, soit le haut de l'échelle 0–51200, entre 20 et 62 °C. La consigne vaut donc **62 °C**, comme Overkiz.
- **L'octet 12 distingue les deux formes :** `0x96` pour MAIN_INFO (28 octets) et `0x8e` pour une borne (20 octets). La longueur de trame radio y est codée. Les deux bornes ont en revanche la même forme et le même octet 12. Elles ne se distinguent que par leur valeur et par l'ordre des demandes.
- **Bornes fixes ou rares :** elles peuvent être lues **une fois par démarrage**, avec une seule demande en cours. Une borne en double ou tardive n'est pas attribuable : en cas de doute, ne rien publier. On peut aussi les vérifier par une relecture (borne haute, borne basse, puis borne haute, la seconde lecture devant donner la même valeur), comme ici.
- **Refus :** aucun refus n'a été observé. Leur forme reste inconnue.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
