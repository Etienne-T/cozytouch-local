# 01 · Reconnaître la carte et câbler la sonde

Matériel vérifié le 17 novembre 2026 : Atlantic 500090 (étiquette 5 V continu, 120 mA), alimentation du bridge, Raspberry Pi Model B Rev 2 avec P1 à 26 broches, alimentation indépendante du Pi, cinq fils courts, multimètre et poste Linux pour piloter la sonde et stocker les copies. L’analyseur logique LA1010 est facultatif pour observer la liaison série. Un adaptateur SWD seul ne convient pas au JTAG de cet ARM9.

1. Coupez les alimentations. Identifiez l’AT91SAM9G25-CU, la RAM Micron D9RZH, la NAND MX30LF1G18AC-TI et le STM32F101RCT6. La radio Si4461 porte le marquage 44612A. Arrêtez si la carte diffère.
2. Orientez la face avec le gros AT91 vers vous. Placez la LED en haut, l’antenne dorée en bas et les ports USB et Ethernet à droite. Les dix pastilles se trouvent au-dessus du processeur, à gauche de la LED. Les photos originales contiennent des identifiants. Le dessin reprend leur orientation.

~~~text
          gauche                    droite
haut      A1 ?    A2 RTCK   A3 ?    A4 GND   A5 VTREF
bas       B1 RST  B2 TDI    B3 TDO  B4 TCK   B5 TMS
~~~

3. Alimentez uniquement le bridge. Mesurez A5 par rapport à A4. Attendu : environ 3,3 V. En cas de doute, coupez et arrêtez.
4. Coupez à nouveau les deux alimentations. Posez les cinq fils suivants. Laissez les autres pastilles libres, notamment le reset. Ne reliez aucune alimentation entre les cartes.

| P1 physique | Signal Pi | Pastille bridge |
|---|---|---|
| 6 | Masse | A4 |
| 19 | BCM10 | B2 |
| 21 | BCM9 | B3 |
| 23 | BCM11 | B4 |
| 24 | BCM8 | B5 |

5. Vérifiez chaque fil dans cette orientation. Vérifiez que SPI et les autres programmes du Pi ont libéré ces GPIO. Le plan d’un autre modèle de Pi reste à qualifier.

[Précédente](README.md) · [Sommaire](README.md#sommaire) · [Suivante](02-sauvegarde-nand.md)
