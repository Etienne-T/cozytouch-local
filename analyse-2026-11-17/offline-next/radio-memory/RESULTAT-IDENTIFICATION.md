# Identification : résultats copiés par le coordinateur

Le 17 novembre 2026, le coordinateur a exécuté les quatre lectures préparées. Cet agent a ensuite relu leurs fichiers locaux. Aucun accès direct au bridge ni émission radio n'a été effectué par cet agent.

Les quatre JSONL privés `donnees/stm32-live-2026-11-17/ident-{ic3-brand,ic3-model,ic3-power,cethi-software}-private.jsonl` possèdent chacun deux callbacks PENDING et un callback final DONE5. Tous ont READ=true, l'adresse et le paramètre attendus, errorType0/errorId0 et un Blob de valeur vide. Les détails libres, groupes et adresses ne sont pas reproduits. La copie nettoyée de cette relecture est `identification-callbacks-reviewed.json`.

Les valeurs utiles proviennent donc du cache Trigger consulté après ces lectures. Le fichier privé `donnees/stm32-live-2026-11-17/ident-cache-private.txt` contient exactement les trois chaînes brutes suivantes, corroborées par `ident-cache-safe.json` :

| Champ IC3 | Octets d'identification | Interprétation du code livré |
|---|---|---|
| Marque | `53` | Sauter. Le catalogue classe cette famille dans les équipements Atlantic ; la marque effective du champ vaut Sauter. |
| Modèle | `41 53 41 4D 41`, puis douze octets nuls | ASAMA, selon la conversion Latin-1 arrêtée au premier nul. |
| Puissance / tension | `D6 06 E6` | `io:PowerState` = 1750 par u16 little-endian ; `io:TensionState` = 230 par u8. Aucune unité supplémentaire n'est déduite de ces seuls fragments. |

Ces valeurs caractérisent le matériel. Elles ne mesurent pas sa consommation instantanée et ne donnent pas sa version de firmware. Le cache n'expose pas ici l'horodatage physique de mesure. Sans une valeur de comparaison immédiatement avant la lecture, le fait qu'il ait été créé ou modifié par ces quatre transactions précises reste non démontré.

Pour CETHI, `definitions-cache-01.jsonl` ligne 3 prouve le composant V4, le subsystemId1, l'URL suffixée #1 et l'état `core:DHWPSoftwareVersionState`. Le coordinateur a consulté cette propriété avec le helper déjà éprouvé. Le fichier `cethi-software-cache-private.txt` est vide. Les tentatives de cache brut à la racine et sur #1 n'ont pas donné de chaîne d'état ; `cethi-software-raw-private.txt` contient uniquement les deux étiquettes de sous-système.

**Aucune nouvelle version logicielle CETHI n'a été obtenue.** E722804 reste une valeur antérieure, à présenter avec sa provenance historique et non comme une mesure du 17 novembre. Les absences Trigger ne prouvent ni un échec radio de la commande, qui a fini DONE, ni l'absence d'une valeur dans tous les caches internes.

Le client Lua reste gelé au SHA-256 `0d9b84b647cc44c6930bb884df6339bf0f041ebb349e2a92cb8316751377ff94`. Le décodeur gelé après correction syntaxique a le SHA-256 `24a690d2ad1e2ff5311943535f88ffb0b4c15477a54fe43da9e4c5625ec947d8` ; `py_compile` et onze tests synthétiques passent. Cette correction ne change ni le client exécuté ni les résultats bruts conservés.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
