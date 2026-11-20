# Cozytouch v6 — expiration des composants MQTT

## Incident du 20 novembre 2026

Le journal de Home Assistant 2026.11.2 signale 12 occurrences depuis le déploiement de la v2. Voici un extrait du journal communiqué pour cette correction.

```text
Invalid MQTT device discovery payload for cozytouch-hub_ic3, not a valid option at 'expire_after'
```

Le journal signale la même erreur pour `cozytouch-hub_cethi`. Home Assistant rejette les deux messages de découverte et ne crée aucune entité.

## Cause et correction

Le service publie un message de découverte MQTT retenu par appareil. La racine contient les options communes et le bloc des composants `cmps`. Home Assistant accepte `expire_after` dans les composants `sensor` et `binary_sensor`. Cette option est interdite à la racine.

`discovery()` place désormais `exp_aft` dans chacun des 21 composants de chaque appareil. Le délai reste égal à `interval_seconds + 45` secondes. Le commentaire qui explique cette marge a été conservé. [service.lua](../../analyse-2026-11-18/persistance-banque-a/phase2/src/service.lua)

## Vérifications hors ligne

- Le nouveau test Lua intercepte les messages retenus produits par le service. Il décode les deux charges avec `lua-cjson`, vérifie la liste blanche des clés racine, puis contrôle le type et l’expiration de chaque composant. Les trois configurations réussissent avec la v6. La v5 échoue sur la clé racine `exp_aft`, comme attendu. [test-discovery.lua](../../analyse-2026-11-18/persistance-banque-a/phase2/tests/test-discovery.lua)
- Les neuf scénarios du test unitaire de session UART réussissent avec les modules v6 extraits du paquet. Les deux scripts Lua historiques de maj-lan-4 réussissent avec leur paquet v4. Ces scripts ne vérifient pas `exp_aft`. Maj-lan-5 utilise le test UART de phase2, qui ne vérifie pas non plus cette option. [test-uart-session.lua](../../analyse-2026-11-18/persistance-banque-a/phase2/tests/test-uart-session.lua)
- Le banc Python vérifie désormais l’expiration par composant. Sa projection de taille maximale compte chaque occurrence. Le fichier Python compile. [test-qemu.py](../../analyse-2026-11-18/persistance-banque-a/phase2/tests/test-qemu.py)

Les tests Lua utilisent LuaJIT ARM et `qemu-arm` en mode utilisateur dans WSL, avec les dépendances locales. Le banc QEMU système n’a pas été lancé. L’acceptation par Home Assistant reste à vérifier après le déploiement.

| Configuration de test | Expiration | CETHI | IC3 |
|---|---:|---:|---:|
| Identifiant `cozytouch-hub`, intervalle de 30 s | 75 s | 5 126 octets | 5 079 octets |
| Identifiant `cozytouch-hub`, intervalle de 60 s | 105 s | 5 147 octets | 5 100 octets |
| Identifiant de 48 caractères, intervalle de 3 600 s | 3 645 s | 6 008 octets | 5 961 octets |

Au format maximal autorisé, les charges restent sous le plafond de 6 144 octets. La marge est de 136 octets pour CETHI et de 183 octets pour IC3.

## Paquet

- Archive CTAPP1 de 65 377 octets. [ct-20261120f.ctapp](../../analyse-2026-11-18/persistance-banque-a/phase2/applications/ct-20261120f.ctapp)
- Version `v-f871bf800c8a`.
- SHA-256 `f871bf800c8ae02f9bc9c46303f4cbb1bac41c1312c954d0680384c88947c777`.

Deux constructions avec `construire-app.sh` dans WSL ont produit les mêmes octets. Les sept modules correspondent aux sources préparées. Chaque empreinte interne a été vérifiée. Seul `service.lua` diffère du paquet v5.

## Déploiement après autorisation du propriétaire

Suivre la séquence utilisée pour la v5. Arrêter la procédure au premier écart. [Rapport v5](../maj-lan-5/RAPPORT.md)

1. Depuis `phase2`, vérifier le SHA-256 de `applications\ct-20261120f.ctapp` avec `Get-FileHash -Algorithm SHA256`. Vérifier aussi la version active avec `.\deployer-app.ps1 -Status`. La version attendue avant l’essai est `v-a581179dd120`.
2. Préparer la v6 avec `.\deployer-app.ps1 -Archive applications\ct-20261120f.ctapp`. Attendre `UPDATE_STAGED version=v-f871bf800c8a files=7` et vérifier que `next` désigne cette version.
3. Déclencher l’essai avec `ct-update reboot` sur le hub. Après le redémarrage, suivre l’état avec `.\deployer-app.ps1 -Status`. Vérifier `HEALTHY=yes`, puis `current=v-f871bf800c8a` et `previous=v-a581179dd120`.
4. Avec un abonné MQTT en lecture seule, vérifier les deux configurations retenues, leurs 21 composants et les états CETHI et IC3, comme pour la v5.
5. Dans Home Assistant, ouvrir **Paramètres → Appareils et services → MQTT**. Vérifier la présence de **Cozytouch CETHI** et **Cozytouch IC3** et la création de leurs entités. Vérifier dans les journaux qu’aucune nouvelle erreur `Invalid MQTT device discovery payload` ne concerne ces appareils depuis le redémarrage.

## Leçon

Les vérifications v2 à v5 abonnaient un client au courtier MQTT. Elles confirmaient la réception des messages. Elles ne vérifiaient pas que Home Assistant acceptait la découverte et créait les entités.

## Déploiement, 20 novembre 2026

<PERSONNE> a autorisé le déploiement applicatif (« génial vas y »). Le redémarrage d’essai a été lancé à 17 h 42 min 44 s, heure de Paris.

- **Avant installation.** SHA-256 vérifié `f871bf800c8ae02f9bc9c46303f4cbb1bac41c1312c954d0680384c88947c777`. Le hub indiquait `HEALTHY=yes`, `current=v-a581179dd120` et `previous=v-1b3e4c30f96c`.
- **Préparation.** Sortie `UPDATE_STAGED version=v-f871bf800c8a files=7`. Le lien `next=v-f871bf800c8a` était prêt et la v5 restait active.
- **Redémarrage.** Sortie `REBOOT_NOW`. La session SSH de redémarrage a été interrompue. La première interrogation SSH a reçu `Connection refused`. La suivante a confirmé `mode=trial running=v-f871bf800c8a`.
- **État final.** Le hub a confirmé `HEALTHY=yes`, `mode=current`, `current=v-f871bf800c8a`, `previous=v-a581179dd120`, `next=-` et `trying=-`.
- **MQTT en lecture seule.** Les configurations retenues CETHI et IC3 ont chacune livré 21 composants, tous dotés de `exp_aft`. Un message d’état a été reçu pour chaque appareil.
- **Home Assistant.** Le contrôle des appareils et des journaux reste à la charge du coordinateur.
