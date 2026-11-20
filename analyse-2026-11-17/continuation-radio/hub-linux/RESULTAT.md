# Réutiliser le hub Cozytouch avec un logiciel maîtrisé

État du 17 novembre 2026. Analyse de la sauvegarde et de sources publiques, complétée par deux lectures d'état natives et une capture UART passive de cinq secondes. Aucun remplacement du système, redémarrage du hub, association ou réglage de chauffage pendant cette étude.

**Oui, réutiliser le matériel actuel est une voie crédible.** La première étape utile est un programme local sous le Linux existant, avec le STM32 et sa radio conservés. Une distribution Linux personnelle est ensuite envisageable. ESPHome peut aussi fonctionner comme application Linux, mais sa compilation ARMv5 et le composant radio particulier restent à qualifier.

## La carte dispose déjà d'un support Linux public

Le DTB de rootB déclare `overkiz,kizboxmini-base`, `atmel,at91sam9g25` et le modèle `Overkiz Kizbox Mini`. La sauvegarde fournit les contrôleurs série, Ethernet, watchdog et NAND. Le noyau actif vérifié lors de l'accès SSH était Linux 5.4.302, architecture `armv5tejl`. Les binaires sauvegardés sont ELF ARM 32 bits little-endian, EABI5 soft-float (`0x05000200`) ; la libc livrée est glibc 2.35. Relevé local reproductible (non publié).

Le noyau Linux officiel v6.12 contient précisément les descriptions [Kizbox Mini base](https://github.com/torvalds/linux/blob/v6.12/arch/arm/boot/dts/microchip/at91-kizboxmini-base.dts) et [commune](https://github.com/torvalds/linux/blob/v6.12/arch/arm/boot/dts/microchip/at91-kizboxmini-common.dtsi), avec les mêmes identifiants. La description commune prévoit 128 Mio de RAM, Ethernet, USART0 et NAND matérielle ECC 4 bits/512 octets. Le découpage bootstrap de 128 Kio puis UBI correspond au DTB sauvegardé. Ce rapprochement établit une base de portage, **pas un test de démarrage d'un nouveau noyau sur cet exemplaire**.

[Buildroot 2025.02.1](https://github.com/buildroot/buildroot/blob/2025.02.1/configs/at91sam9x5ek_defconfig) contient une configuration pour la famille SAM9x5 et sa carte d'évaluation SAM9G25. Elle n'est pas une image Cozytouch prête à flasher. La recette OpenWrt SAM9x consultée propose aussi la carte d'évaluation, mais aucun profil Kizbox Mini n'a été trouvé dans ce fichier. Un tel profil devrait être développé et validé, notamment pour le démarrage, UBI et le watchdog. Les snapshots retenus et leurs empreintes sont dans sources.json (non publié).

## Ce qu'ESPHome peut apporter

La documentation ESPHome consultée affiche **2026.10.2**. Sa [plateforme host](https://esphome.io/components/host/) compile une configuration en programme Linux ou macOS. Son [UART host](https://esphome.io/components/uart/#uart-on-host) accepte un chemin de port Unix, à la place des broches TX/RX.

Cela ouvre une piste `ESPHome host → /dev/ttyS1 → STM32`. Ce n'est pas une preuve que le générateur compile immédiatement pour ARM926EJ-S : il faut une chaîne de compilation ARMv5 soft-float, des bibliothèques compatibles et un composant MRIO personnalisé. La présence d'un UART générique ne fournit pas les profils IC3/CETHI, la gestion des sessions, les clés ni les réponses asynchrones.

Le binaire ESPHome Linux fonctionnerait **au-dessus de Linux** ; il ne remplacerait pas à lui seul le noyau ou le système de fichiers. Installer ESPHome directement dans le STM32 est une autre opération : la plateforme STM32F101 et cette carte radio ne sont pas qualifiées ici, et cela remplacerait précisément la pile io-homecontrol déjà opérationnelle. Ce n'est pas le chemin retenu pour réutiliser cette pile.

## Trois niveaux de remplacement

| Route | Développement nécessaire | État |
|---|---|---|
| Petit service local utilisant les commandes natives du daemon | Encapsulation des READ qualifiés, conversion des états, exposition locale MQTT/API | Le transport D-Bus et les READ IC3/CETHI sont déjà prouvés ; l'adaptateur HA autonome et l'essai WAN isolé restent à réaliser |
| Notre programme Linux parlant directement au STM32 | Protocole MRIO, initialisation, identités/clés, files de commandes, événements et profils Atlantic | Fondations disponibles ; aucun remplacement du daemon encore testé |
| Linux personnel avec le même STM32 | Travail précédent, plus image de démarrage, pilotes, watchdog, stockage et retour au système original | Support carte public établi ; aucune nouvelle image compilée, démarrée ou flashée |

La variante ESPHome host peut servir à la seconde route. Un service C/C++ ou Lua avec MQTT est également possible. Le choix dépendra du coût de portage du protocole et de la compilation, pas d'une obligation de changer le matériel.

```mermaid
flowchart LR
  HA[Home Assistant] -. "À développer : API ou MQTT" .-> L[Notre service sous Linux]
  L -. "À qualifier : pilote MRIO" .-> S[STM32 conservé]
  S --> R[Radio Si4461 existante]
  R --> A[ASAMA et chauffe-eau]
```

Les liens en pointillés sont proposés. Le chemin STM32/radio/appareils est déjà utilisé par le système original. Source du schéma conservée ; rendu non vérifié.

## Ordre d'essais recommandé

1. Construire le codec et la machine d'états à partir des captures conservées, en tests hors ligne avec données synthétiques et secrets masqués.
2. Tester un service en RAM sous KizOS, avec un propriétaire unique de `/dev/ttyS1`. Deux programmes ne doivent pas lire le même UART simultanément : ils se partageraient les réponses.
3. Qualifier une lecture d'état avec retour au service d'origine, puis les fonctions par profil exact. Préserver la différence IC3 `52/1` et CETHI `51/0`.
4. Vérifier séparément le fonctionnement avec le WAN isolé, y compris le démarrage et les délais. Les lectures locales déjà réussies avec le réseau normal ne démontrent pas cette autonomie.
5. Seulement ensuite préparer un Linux minimal, d'abord en RAM avec noyau/DTB conservés et watchdog maîtrisé. La NAND, le bootstrap et les sauvegardes d'origine restent la référence de retour. Aucun flash n'est nécessaire pour les premières preuves.

## Correction documentaire issue de la contre-revue

Le script de décodage final de la collecte précédente avait fourni les étiquettes de profils à l'envers. Les requêtes avaient ciblé les bons appareils ; les octets, les acquittements DONE et les preuves d'absence d'erreur restent valides. Le nouveau décodage corrigé (non publié) utilise IC3 `52/1` et CETHI `51/0`, sans modifier les captures ou l'archive historique. Il retrouve le mode confort IC3 et la valeur normalisée CETHI, sans en déduire une température.

## Contre-épreuve sur le hub à 20 h 52 CET

Deux requêtes natives `main-parameter`, d'abord CETHI puis IC3, ont terminé **DONE/IoCommandNoError**. L'observateur a capturé cinq secondes du descripteur série du daemon, puis s'est détaché avec contrôle de son identité et de `TracerPid=0`. Il n'a pas ouvert l'UART et n'a injecté aucune commande dans le processus.

Les quatre trames totalisent 162 octets : deux requêtes `0x0100`, payload de 39 octets, et deux réponses `0x010d`, payload de 28 octets. Leurs CRC sont valides, sans candidat rejeté ni octet restant. Pour chacune des deux requêtes, le bloc de 16 octets à l'offset 18 du payload est égal au champ `stack1.key` de la sauvegarde Linux. Aucune valeur de clé ni adresse privée n'est exportée. Cette observation confirme la transmission de ce contexte par Linux pour **ces deux lectures** ; elle ne prouve pas que toute commande utilise toujours la même clé.

Les preuves sont dans qualified-capture-verification.json (non publié), qualified-cethi-decoded.json (non publié) et qualified-ic3-decoded.json (non publié). Les captures brutes restent privées dans `qualified-private/`. À **20 h 54 min 10 s CET**, le daemon conserve son PID et son instant de démarrage, possède toujours l'UART et n'est plus tracé. Aucun motif de timeout, référence invalide ou reset radio n'est trouvé depuis le début de la capture : contrôle différé (non publié).
