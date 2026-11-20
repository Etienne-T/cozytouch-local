# Première mise à jour par le réseau local — 20 novembre 2026

**But :** corriger le délai de santé de 95 secondes, et faire le premier vrai essai de `ct-update` sur le hub.

## Défaut corrigé

**Avant :** dans la v4 d'usine, le service comptait 95 secondes depuis son démarrage. Si le courtier MQTT de Home Assistant répondait plus tard, le service s'arrêtait avec le code 31 et la LED passait au rouge. C'est le cas après une coupure de courant générale, quand Home Assistant redémarre plus lentement que le hub. Le compteur kboot n'était pas remis à 0. Deux démarrages ratés de suite renvoyaient donc sur la banque B.

**Après :** les 95 secondes ne comptent que le temps où la session MQTT est établie (`connected_seconds` dans `phase2/src/service.lua`).
- **Courtier absent :** le service attend sans limite de durée, en LED verte clignotante. Il ne lance aucune lecture radio et réessaie de se connecter toutes les 16 secondes au plus.
- **Courtier connecté mais défaillant :** le service s'arrête avec le code 31 après 95 secondes de session cumulées, et affiche `HEALTH_TIMEOUT`.

## Archive

| Élément | Valeur |
|---|---|
| Fichier | `phase2/applications/ct-20261120a.ctapp` (6 modules, 39 647 octets) |
| SHA-256 | `bd5f7e61b4ea7b8c3134b43dff0e2b7cd6a4d2a532cabbc70d385745eb5e3555` |
| Version sur le hub | `v-bd5f7e61b4ea` |
| Construction | `bash phase2/construire-app.sh phase2/applications/ct-20261120a.ctapp` (WSL) |

## Tests QEMU (`phase2/preuves/late-broker-20261120.log`)

Les tests ont tourné sur la base root A v4 déployée (`42fa0625…`), avec cette archive exacte en essai (`CT_CANDIDATE_APP`).
- **`late-broker-v4` :** l'application d'usine abandonne à 95 secondes. Le défaut est donc reproduit.
- **`late-broker` :** le courtier reste absent 110 secondes. Pendant ce temps, aucune lecture et aucune sortie du service. Une fois le courtier démarré :
  - les deux lectures ont lieu, suivies de `HEALTH_OK` ;
  - le compteur revient à 0 ;
  - l'essai est promu en `current`.
- **Non-régression :** `healthy`, `outage`, `ota-trial`, `ota-fail`, `term` et `lwt` passent.

## Étapes sur le hub, à autoriser par <PERSONNE>

1. `.\phase2\deployer-app.ps1 -Archive phase2\applications\ct-20261120a.ctapp -Reboot` :
   - envoi de l'archive et contrôle de son SHA-256 ;
   - `next` est créé ;
   - le hub redémarre.
2. Attendre environ 1 minute 30, puis lancer `.\phase2\deployer-app.ps1 -Status`. Résultat attendu : `mode=current`, `current=v-bd5f7e61b4ea`, `previous=-`, et la LED verte fixe.

## Exécution, 20 novembre 2026 vers 9 h 20 (heure de Paris), autorisée par <PERSONNE> (« c'est parti »)

1. **Installation :** `ct-update install` a réussi (`UPDATE_STAGED version=v-bd5f7e61b4ea files=6`). Le script PC a pourtant affiché « Installation refusée » et n'a pas redémarré le hub.
   - **Cause :** dans `Invoke-Hub`, PowerShell renvoyait la sortie SSH avec le code de retour.
   - **Correction :** la sortie passe maintenant par `Out-Host` (`deployer-app.ps1`).
   - `-Status` a confirmé `next=v-bd5f7e61b4ea valid=true`, en mode factory.
2. **Redémarrage :** `ct-update reboot` affiche `REBOOT_NOW`. La session SSH reste ensuite bloquée, ce qui est normal avec `reboot -f`.
3. **Essai réussi :** sain à 50 secondes de fonctionnement.
   - `/run/ct/healthy` est présent ;
   - la LED est verte fixe (vert 255, rouge 0, déclencheur `none`) ;
   - `APP_STATUS mode=current running=v-bd5f7e61b4ea` ;
   - `current=v-bd5f7e61b4ea`, sans `previous`, `next` ni `trying`.

   La version d'essai a donc été promue après `HEALTH_OK`, ce qui valide le mécanisme sur le hub.

## Si l'essai échoue

Le hub abandonne la version et redémarre une fois sur l'application d'usine, qui remet le compteur à 0.

Après une coupure de courant pendant l'essai, le démarrage suivant supprime `trying` et lance l'application d'usine.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
