# Cozytouch — JTAG et sauvegarde NAND du 17 novembre 2026

<PERSONNE> rend disponible le Raspberry Pi Model B Rev 2 `<CHEMIN_LOCAL>`, connecteur P1 a 26 broches. Il servira de sonde GPIO JTAG sous OpenOCD. Le HP servira au pilotage SSH et a la conservation des dumps. Le mini ST-Link inventorie expose SWD et ne constitue pas une sonde JTAG ARM9 utilisable pour ce montage. Le LA1010 peut conserver son role d'observation UART.

État du 17 novembre 2026 : JTAG identifié (0x0792603f), NAND de 128 Mio acquise avec ses 4 Mio d'OOB. Une seconde lecture complète vérifie les 64 lots par SHA-256 calculé sur le processeur du bridge. Les empreintes concordent avec l'image sauvegardée. Copies Windows et HP, ainsi que l'archive finale, vérifiées par SHA-256. Fiche et fichiers (non publié). Les incidents de transfert, les reprises et les preuves sont dans [ACQUISITION.md](ACQUISITION.md). OpenOCD est arrêté et les GPIO JTAG du Pi sont en entrée.

## Reperes physiques

Face composants avec le gros AT91 visible, LED en haut, antenne doree en bas, USB et Ethernet a droite. Le groupe JTAG est le rectangle de dix pastilles au-dessus du processeur, a gauche de la LED. A = rangee du haut, B = rangee du bas ; numeros locaux de gauche a droite, pas une numerotation standard.

```text
       A1       A2       A3       A4       A5
       ?       RTCK      ?       GND     VTREF

       B1       B2       B3       B4       B5
      #RST      TDI      TDO      TCK      TMS
```

Repères du billet Lafois, concordance visuelle avec la carte de <PERSONNE>. VTREF mesuré à 3,3 V par <PERSONNE> ; communication JTAG vérifiée après contrôle du câblage. Continuité non mesurée.

| Pi : broche physique P1 | GPIO BCM | Cozytouch |
|---|---|---|
| 6 | GND | A4 GND |
| 23 | GPIO11 | B4 TCK |
| 24 | GPIO8 | B5 TMS |
| 19 | GPIO10 | B2 TDI |
| 21 | GPIO9 | B3 TDO |

Avant raccordement, mesurer VTREF A5 par rapport a GND A4, Cozytouch seul alimente. Le raccordement direct exige environ 3,3 V. Si autre tension, ne pas relier les GPIO. Puis couper les alimentations pour poser les cinq fils courts et fixes. Aucun fil entre les alimentations des deux cartes : ne pas relier VTREF au 3,3 V du Pi, ni les 5 V. A1/A2/A3/A5/B1 restent libres au premier essai. Le reset #RST reste a qualifier avant toute connexion ; le premier scan n'en a pas besoin. Verifier que les GPIO du Pi ne servent plus au montage Yoto et ne sont pas pris par SPI ou un autre processus.

Le Pi doit executer OpenOCD ; le HP ne peut pas piloter directement ces GPIO par son propre pilote bcm2835gpio. Une fois le modele, le pilote, les GPIO et le cablage verifies, le premier test sera `sudo openocd -f scan-pi-b.cfg`. Il scanne le TAP sans commande d'arret CPU ni lecture NAND. Une absence de reponse ne prouve pas un verrouillage : controler cablage, niveau logique, vitesse et reset.

## Sauvegarde obtenue

L'image `nand-full-A-data-oob.raw` contient 65536 pages physiques de 2048 octets suivis de leurs 64 octets OOB. Aucun bloc n'est sauté. Les contrôles de chaque transfert utilisent un CRC calculé sur le processeur. La relecture complète recalcule en plus un SHA-256 par lot sur le processeur ; toutes les empreintes concordent avec l'image sauvegardée. Aucun second fichier brut n'est synthétisé à partir de A.

Voir le résultat local (non publié) et [la procédure détaillée](ACQUISITION.md). La routine NAND accélérée intégrée d'OpenOCD a échoué ; les scripts ARM conservés contournent cet incident. Les transferts rejetés restent dans les preuves et ne doivent pas servir d'images de référence. Aucun effacement ou programmation NAND. La flash interne du STM32 radio et la restauration sur matériel ne sont pas couvertes par cette sauvegarde.

Sources : [reperes Lafois](https://www.lafois.com/wp-content/uploads/2020/10/jtag_usb-1-917x1024.png), [procedure NAND du billet](https://www.lafois.com/2020/11/08/rooting-the-cozytouch-aka-kizbox-mini-part-2/), [brochage Pi OpenOCD 0.12.0](https://github.com/openocd-org/openocd/blob/v0.12.0/tcl/interface/raspberrypi-native.cfg), [commandes NAND OpenOCD](https://openocd.org/doc-release/html/Flash-Commands.html#NAND-Flash-Commands).

## Historique : deuxième scan JTAG

Apres verification du cablage par <PERSONNE>, second scan autorise et execute a 5 kHz : TAP Atmel detecte, IDCODE 0x0792603f conforme a la cible attendue. Journal : scan-02.log. Aucune erreur de capture IR dans ce scan, aucune commande halt, reset systeme ou acces NAND. Les GPIO 8/9/10/11 sont revenus en entree apres sortie. Le premier echec est conserve comme historique ; sa cause physique exacte n'est pas etablie. La sauvegarde NAND reste a preparer et executer.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
