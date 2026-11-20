# Client UART autonome : lectures réussies avec Internet bloqué

**Le 17 novembre 2026, le client LuaJIT développé pour cette carte a lu le paramètre principal du Calypso et de l'ASAMA, avec le daemon radio constructeur arrêté. Les deux lectures ont aussi réussi sous blocage réseau IPv4 et IPv6.** Le client n'utilise ni module constructeur, ni D-Bus, ni service cloud. Le STM32 conserve son firmware original v2.4.2 et était déjà initialisé avant l'essai.

Le test a commencé à **21 h 09 min 31 s CET**. Le réseau et le daemon constructeur sont rétablis. À **21 h 11 min 54 s CET**, le contrôle différé ne trouve aucun motif d'erreur radio ; les deux lectures via le daemon restauré ont également terminé sans erreur. Aucun réglage de chauffage, association, reset du STM32, déprotection ou programmation de Flash n'a été demandé par le client.

## Résultats des quatre lectures

| Appareil | Réseau normal | Réseau isolé | Valeur brute cible/courante |
|---|---|---|---|
| Chauffe-eau CETHI V4, profil 51/0 | DONE, 69 ms | DONE, 72 ms |51200/51200 ; valeur normalisée, pas une température |
| Sèche-serviettes IC3, profil 52/1 | DONE, 85 ms | DONE, 111 ms |64517/64517 ; correspond au mode confort dans les convertisseurs livrés |

Chaque demande est reconstruite à partir des champs de contexte privés sauvegardés et du schéma connu. Le client produit seulement `ACTIVATE_STATUS_REQUEST/MAIN_INFO` dans l'enveloppe `0x0100`, puis attend `0x010d` avec adresses, commande et statut correspondants. Il ne rejoue pas une trame radio enregistrée : le STM32 traite la session radio courante.

Les réponses indiquent `command_status=0`, `execute_status=5`, `detailed_status=0`. Aucun CRC rejeté, bruit, callback ancien ou callback ignoré pendant ces quatre demandes. Les valeurs brutes ne démontrent pas une nouvelle mesure physique de température ; le test porte sur la lecture d'état principal.

Preuve structurée : orchestration/verified-results.json (non publié). Journaux expurgés : essai (non publié), retour corrigé (non publié), lectures natives restaurées (non publié), santé différée (non publié).

## Portée exacte du test sans Internet

Quatre chaînes temporaires ont été placées en tête des règles INPUT/OUTPUT IPv4 et IPv6. Elles ont autorisé seulement loopback et le pair SSH IPv4 exact sur TCP 2222. Tout autre trafic IP entrant/sortant, y compris les connexions cloud déjà établies et le DNS, était bloqué. Aucune route alternative par le LAN n'était autorisée par ces règles.

Les sondes réseau IPv4 et IPv6 ont échoué pendant l'isolement. Les compteurs DROP montrent respectivement **1 paquet / 84 octets** et **1 paquet / 104 octets**, correspondant aux sondes émises. Les deux READ radio ont ensuite réussi dans un **nouveau processus client**. Après le test, les sorties `iptables -S` et `ip6tables -S` sont identiques octet par octet à celles conservées avant l'essai.

Cela démontre une lecture locale avec le **client autonome et le STM32 déjà démarré**, sans Internet pendant la transaction. Cela ne démontre pas encore le démarrage sans cloud après une coupure d'alimentation, la reconnexion après reset STM32, les commandes d'écriture, l'association ou l'autonomie durable de tous les services.

## Client et garde-fous

- cozytouch-read.lua (non publié) : source du client testé, SHA-256 `51c5b3cb4801203e61b99e2abee7fb7ca5242fe578b95513d6a121f1c1914bea`.
- README du client (non publié) : schéma, CLI et limites. La configuration privée contient les contextes des deux appareils ; elle ne doit pas être publiée.
- Le client refuse tout autre propriétaire de l'UART, utilise `flock` et `TIOCEXCL`, vérifie 115200/8N1 et restaure les réglages en sortie.
- Il n'émet que les deux READ autorisés, avec 8 secondes par demande et 19 secondes au total. Il arrête au premier échec, sans retry implicite ni commande de découverte.
- L'orchestration suspend temporairement la supervision, arrête complètement le daemon constructeur et arme un retour indépendant après 90 secondes. Elle conserve le réseau d'administration et l'accès SSH en RAM.

Tests hors matériel exécutés sur le LuaJIT du hub : CRC connu, tous les découpages de trame, fragmentation octet par octet, bruit, longueur invalide, CRC invalide, réponse tardive, timeout, mauvaise cible/commande, statut d'erreur et notification de reset. La comparaison supplémentaire aux deux captures qualifiées est passée : verify-offline-fixed.txt (non publié). Elle n'ouvre aucun UART.

## Incident de retour et corrections conservées

Les quatre lectures ont réussi dès le premier essai. Le script de retour avait ensuite rétabli le réseau, mais son option shell `set -u` était incompatible avec une variable facultative du script constructeur `kizosenv.sh`. La relance radio s'est arrêtée sur `OVKSECURITYDIR: parameter not set`. Le coordinateur a retiré cette option avant le chargement de l'environnement constructeur, puis relancé le retour. Le daemon PID 10699 et sa supervision sont rétablis ; `IO_UPDATE_SCRIPT=/bin/false` reste limité à cet environnement RAM. Deux READ natifs et le contrôle différé confirment le fonctionnement normal.

Le journal original conserve donc un code de sortie 91, même si les quatre lectures sont réussies. Il ne doit pas être présenté comme un essai dont la restauration automatique a réussi sans intervention. Le script corrigé et sa preuve de retour sont conservés séparément. Aucune nouvelle émission de test autonome n'était nécessaire pour corriger cet incident d'orchestration.

Le test de fixtures supplémentaire avait aussi un motif de label limité aux lettres, qui rejetait `IC3`. Le motif a été corrigé pour inclure les chiffres, puis le test hors ligne est passé. Le code client déployé et testé n'a pas changé.

## Clés : la preuve actuelle et ce qui reste

Les deux requêtes utilisent le contexte de 16 octets égal à `stack1.key` sauvegardé. Le nouveau client l'a fourni au STM32 sans le daemon constructeur, et les deux appareils ont répondu, y compris réseau isolé. **L'accès au contexte de clé n'est donc plus un blocage pour ces deux lectures à chaud.**

Les clés d'actionneur, l'ancienne clé de pile et `oldSystemKey` restent des objets distincts. Leur sélection générale n'est pas déduite de deux exemples. Le STM32 charge le contexte UART en SRAM et conserve ses mécanismes radio ; l'application Linux n'a pas besoin de réimplémenter AES pour le chemin testé. L'initialisation à froid et les autres opérations restent à qualifier.

**Cursor/Grok a réellement exécuté la revue demandée** : CLI `2026.11.13-eacade1`, modèle demandé et disponible `grok-4.7-high`, succès en 7 min 49 s. Les 17 fichiers expurgés et la mission sont restés inchangés. L'envoi, d'abord refusé par le contrôle automatique, a été effectué après l'accord explicite de <PERSONNE> sur ce corpus et cette destination. Aucun dump brut ni valeur de clé n'a été envoyé.

Le [rapport original Grok](cles-cursor/RAPPORT-GROK.md) est accompagné d'une [contre-vérification](cles-cursor/REVUE-DU-RAPPORT-GROK.md). Six formulations trop générales ont été corrigées ou bornées, notamment la longueur générique de sortie cryptographique et les conclusions sur la sélection de clé. Un désassemblage Thumb supplémentaire confirme que le chemin étudié sauvegarde le bloc SRAM courant dans le bloc secondaire, puis installe la clé entrante. Cela ne donne pas automatiquement à ces deux blocs la sémantique des champs Linux `key`/`oldKey`.

Grok a reçu le corpus figé avant la réussite du client autonome. Ses réserves sur l'absence de cet essai restent fidèles à son entrée, mais sont dépassées par les quatre lectures documentées ici. La synthèse locale actualisée (non publié) conserve cette distinction.

## AquaMQTT et fonctions supplémentaires

La comparaison [AquaMQTT–Calypso](aqua/RESULTAT.md) a identifié trois sondes natives : air entrant `0x0c001a01`, évaporateur bas `0x0c001b01` et évaporateur haut `0x0c001c01`. La qualification complémentaire (non publié) établit leur enregistrement C++ pour CETHI 51/0, leur encodeur GenericV2 et leur construction READ avec valeur vide. Les numéros du bus filaire AquaMQTT ne sont pas employés comme indices radio.

Un dérivé D-Bus limité à ces trois READ a passé ses trois contrôles de construction sur le hub. **Seule la lecture air entrant a été envoyée.** Elle a reçu un callback corrélé DONE/command DONE, mais avec code 0/0 et Blob vide, au lieu du résultat 1/1 accompagné d'une valeur des lectures principales. Ce résultat est **non concluant** : aucune température récupérée et aucune preuve suffisante d'une transaction radio réussie. Les deux sondes d'évaporateur n'ont donc pas été testées. Aucune unité n'a été inventée. Résultat décodé (non publié).

Le contrôle de santé à 21 h 22 min 56 s CET (non publié) confirme le même daemon PID10699, propriétaire normal de l'UART, aucun traceur ni processus de mise à jour, zéro motif d'erreur radio depuis le retour et les règles IPv4/IPv6 restaurées exactement. La cause du retour vide reste à analyser ; elle ne démontre pas que la sonde physique est absente.

AquaMQTT documente aussi activité PAC/appoint/ventilateur, dégivrage, vitesse ventilateur et historique des erreurs. Une donnée visible sur le bus interne peut ne pas être exposée par radio. Les décalages d'octets du bus HMI ne sont pas des numéros de registre io. Certaines autres fonctions, comme températures d'eau, défauts et puissances, avaient déjà des définitions dans notre catalogue.


La contre-revue du code GenericV2 précise que `analyze` peut déposer la valeur dans StateManager puis terminer avec `DetailedError()` par défaut : le couple 0/0 et le Blob vide du callback ne prouvent donc pas un refus ou une absence d'émission. Une consultation passive du cache Trigger brut sur l'objet CETHI sans suffixe retourne `namespace.isnil` pour les trois identifiants. Les traces stdout/stderr sont conservées sous `extra-read/cache-private.txt*`. Cela constate une entrée absente sur cette route, pas l'absence de sonde physique. La prochaine preuve utile est une réponse UART décodée ou un événement d'état corrélé, sans élargir les commandes envoyées.

## Difficulté relative après cette preuve

| Solution | Difficulté restante | Raisons principales |
|---|---|---|
| Service local sur Linux conservant STM32/MRIO | Modérée, meilleure voie pour les deux appareils | Lecture autonome prouvée ; restent démarrage froid, service durable, profils utiles et API/MQTT. |
| ESPHome host sur le hub | Plus élevée | Même pilote MRIO, plus compilation ARMv5 et adaptation ESPHome. Aucun gain immédiat sur la radio. |
| ESP32 et radio indépendante supportée | Élevée, mais projet public disponible | Adaptation ASAMA/CETHI exacts, identité et clés, matériel RF et qualification des fonctions. |
| Nouveau Linux complet sur le hub | La plus élevée pour réemployer toute la carte | Ajoute boot, NAND/ECC/UBI, pilotes, watchdog et restauration à la partie protocole. |
| AquaMQTT filaire | Conditionnelle à la compatibilité matérielle | Logiciel existant pour des modèles voisins ; connectique et protocole 286041/CV4 à identifier. Seulement le Calypso. |

La suite logique est de rendre le service local durable et observable, puis de vérifier sa reprise après reset. Le remplacement complet de l'OS n'est pas nécessaire pour exposer les deux appareils localement. La tâche Inbox de lecture locale sans cloud a maintenant une preuve de réalisation ; sa clôture reste à proposer, sans modifier automatiquement la case.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
