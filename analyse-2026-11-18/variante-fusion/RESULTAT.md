# Cozytouch RAM4 — fusion noyau allégé et service UART/MQTT

**18 novembre 2026. Une seule variante SAM9G25 a été construite et auditée. Le contenu utilisateur a passé la qualification QEMU ARM926. Le staging est vérifié hors ligne. La fusion n’a pas démarré sur le hub.**

## Images et provenance

| Fichier | Octets | SHA-256 |
|---|---:|---|
| `zImage` | 3 316 832 | `68f0a3243ee095ed73ad95fc48486174c281e8ce16d04db0bb0d534ec1cd205c` |
| `ram4-final.dtb` | 18 520 | `8b94225588aa53ca5a2624b5ee18d3f66e7275a679b08a89a31f122d949b1e55` |
| `rootfs.cpio.gz` | 3 514 947 | `fcf6ea211338de9453551d940c2d7c991dd730637876903aeb52899987e430cf` |

- **Taille du noyau :** 4 189 096 octets pour le service essai04, 3 331 528 octets pour la variante durcie, 3 316 832 pour la fusion. Le gain face à essai04 est de 872 264 octets (20,82 %). La fusion retire 14 696 octets supplémentaires par rapport à la variante durcie.
- **Construction isolée :** `<CHEMIN_LOCAL>` sur le HP. Buildroot 2026.08 extrait de son archive vérifiée, `output/` neuf et cache de téléchargements partagé. Linux 6.12 et toolchain Bootlin ARMv5 EABI glibc 2025.08-1. Recette (non publié) · Sources épinglées (non publié) · Journal (non publié).
- **Deltas noyau :** CAN, Wi-Fi/cfg80211 et données réglementaires, NFS/SUNRPC, ALSA et SIT/6RD retirés. Le Kconfig résolu perd 93 options actives et 3 valeurs dépendantes, sans nouvelle activation. Pas de `STRICT_KERNEL_RWX`, d’`ARM_DEBUG_WX`, de `DEBUG_ALIGN_RODATA` ni de `CRYPTO_JITTERENTROPY`. IPv6 et `ip6tables` legacy restent intégrés. Fragment (non publié) · [Kconfig résolu](images/kernel.config).
- **Service :** les sept modules, les autres fichiers de l’overlay service et les trois ELF LuaJIT/cjson sont identiques à la référence essai04. `/init`, la politique réseau et les fichiers d’administration protégés sont également identiques. Le CPIO n’ajoute ni ne retire d’entrée ; quatre fichiers annexes sont reconstruits (`json2lua`, `lua2json`, le script GDB de libstdc++ et `xtables-legacy-multi`). Les deux wrappers cjson ne diffèrent que par les chemins de sortie. Aucune cible réelle dans le CPIO. Les images et la charge restent privées : l’initrd conserve l’overlay SSH privé déjà approuvé pour essai04.

## Vérifications hors ligne

- **Audit final OK :** 43 fonctions requises intégrées, 29 fonctions interdites absentes. Le flux décompressé du `zImage` correspond à l’`Image` Kbuild. Le DTB est identique à la référence hors bornes initrd : `0x24000000–0x2435a243`, borne haute exclusive. Budget RAM théorique : 104,91 Mio avant allocations. Audit final (non publié) · Audit cœur rejoué sous Windows (non publié) · Empreintes des images (non publié).
- **Tests du dépôt :** 94 tests `unittest` et 12 cas RPC simulés réussis sous Windows. Aucun processus OpenOCD réel ni connexion au hub. Tests (non publié) · RPC hors ligne (non publié). Les SHA-256 des 48 fichiers transférés depuis le HP concordent. Manifeste du transfert (non publié).
- **QEMU 10.2.1, ARM926 VersatilePB :** ELF32 ARMv5 EABI5 soft-float, SONAME `libluajit-5.1.so.2`, symboles `luaopen_cjson` et `luaopen_cjson_safe`. `require('ffi')`, `require('cjson')` et `require('cjson.safe')` réussis. ABI `4/36/17/11`, `TCGETS` sur PTY, selftests UART/MQTT et deux fixtures synthétiques avec toutes les coupures validés. Mosquitto local : deux PUBACK, QoS1 et LWT `offline` retenu vus par un abonné indépendant. Aucun UART réel ouvert. Qualification (non publié).
- **Réseau et stockage QEMU :** SSH par clé et PTY `/dev/pts/0`. IPv6 présent et désactivé avant la montée des interfaces, `ip6tables` legacy utilisable. IPv4 DROP avant montée réseau ; aucune route par défaut ; sonde WAN synthétique : compteur OUTPUT DROP +1. Aucun MTD, UBI, bloc ni `/dev/mem`. Console (non publié). Le banc utilise le CPIO fusionné avec un init de test, des clés jetables et un noyau VersatilePB séparé. Il ne valide ni le démarrage du `zImage` SAM9G25 ni son watchdog ou son UART physique.

## Staging et validation matérielle séparée

La charge Pi (non publié) est prête et son reçu (non publié) fixe le SHA-256 `90679fdb6f9be408a0dca9cd26c1ffc248fd2be36e966d7fd46d5a7884da8d6a`. Le lanceur de référence a validé les empreintes et le plan RAM à blanc avec un identifiant synthétique. L’archive ne contient pas de script de déclenchement. Aucun accès au Pi, au JTAG ni au hub ; aucun lancement matériel, aucun changement sur le PKM.

Avant un essai matériel :

1. Obtenir l’autorisation explicite pour cette fusion. Vérifier l’état courant du hub, la disponibilité du SSH OEM temporaire et du retour OEM. Ne pas déduire ces états du seul essai04.
2. Reprendre la procédure P1 de [mise au repos OEM](../internald-quiescence-grok/RAPPORT.md) et son [complément](../internald-quiescence-grok/RAPPORT-COMPLEMENT.md) : garder `internald` et le watchdog actifs, exclure une mise à jour ou un redémarrage en cours ou planifié, vérifier les écrivains avant `sync`, puis confirmer les trois volumes en lecture seule et l’absence d’écriture résiduelle. Arrêter si un prérequis manque.
3. Après autorisation, vérifier charge, empreintes, plan local et retour OEM sur le Pi. Respecter le préflight matériel et vérifier les relectures RAM avant le démarrage. Ne pas réutiliser une ancienne preuve de quiescence. Le retour RAM4 vers l’OEM exige la continuité vérifiée du chemin USB quiescé ; ne pas réutiliser cette procédure après un reset ou si le contexte est inconnu.
4. Valider le boot SAM9G25, watchdog, réseau, stockage absent, SSH/PTY puis deux lectures CETHI/IC3 et trois cycles MQTT bornés. Vérifier la restauration UART et le retour OEM. Ne lancer aucune commande de chauffe, d’appairage, d’updater, de flash ou d’accès brut NAND/MTD.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
