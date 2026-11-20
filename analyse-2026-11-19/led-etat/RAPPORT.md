# LED d'état du Kizbox Mini : câblage, pilotage OEM et commande depuis la banque A

Analyse **hors ligne**, en lecture seule, le 19 novembre 2026. Sources : extractions OEM du 17 novembre (`rootB`, `appsB`, volumes NAND), modules Lua d'`internald` décompilés, nos sources de la phase 2. Aucun accès au hub, au réseau ou à un compte. Aucune commande lancée sur le matériel. Ce rapport ne décrit pas l'état actuel du hub, sauf la couleur orange rapportée par <PERSONNE>.

Légende : **Observé** = lu dans un fichier cité. **Déduit** = conséquence logique de plusieurs observations. **Supposé** = connaissance générale du noyau ou du SoC, non vérifiée dans ce dépôt (aucune source C du noyau n'est disponible ici).

Chemins relatifs à `../..`.

## 1. Verdict

- La LED d'état est **bicolore rouge/vert**. Le système d'origine ne la pilote pas en GPIO simple mais par le **contrôleur PWM0 du SAM9G25** (`pwm@f8034000`), au travers du pilote `pwm-leds` et de `/sys/class/leds/pwm:{red,green}:user`.
- **Vert = PWM0 canal 0 sur PC10** (fonction périphérique C). **Rouge = PWM0 canal 1 sur PC11** (périphérique C). Un canal bleu (canal 2, PC20) est déclaré mais désactivé. L'**orange** n'est pas une couleur distincte : c'est rouge 100 % + vert 100 %.
- **L'orange est l'état « démarrage » de l'OEM.** K-Boot (Linux 4.1.31) l'allume avec `linux,default-trigger = "default-on"` sur les deux canaux. Notre noyau 6.12, lancé par `kexec`, ne déclare ni le PWM ni les LED, et personne ne vient ensuite écrire d'autre couleur. La LED reste donc dans l'état laissé par K-Boot.
- **Le plus simple pour nous :** ajouter au DTS `durable` les nœuds `&pwm0` et `pwm-leds`. Les pilotes nécessaires sont **déjà compilés en dur** dans notre noyau (`CONFIG_PWM_ATMEL=y`, `CONFIG_LEDS_PWM=y`). Une reconstruction du DTB suffit, sans reconstruire le noyau. Solution de secours sans changer le DTS : piloter PC10/PC11 en GPIO via `/dev/gpiochip2` avec luajit (script proposé `led-etat.lua`, jamais exécuté).
- **Aucune broche LED n'est partagée** avec la radio (PA0…PA6), les boutons, les straps de modèle ou la NAND.

## 2. Câblage et polarité

| Couleur | Canal | Broche | Fonction | Polarité | Statut OEM | Preuves |
|---|---|---|---|---|---|---|
| Vert | PWM0 ch 0 | **PC10** | périph. C, sans pull | active haut (**supposé**) | activé, `default-on` | observé : `analyse-2026-11-19/led-etat/oem-rootB-kizboxmini-base.dtb.txt:359-361`, `:999-1004` |
| Rouge | PWM0 ch 1 | **PC11** | périph. C, sans pull | active haut (**supposé**) | activé, `default-on` | observé : même fichier `:369-371`, `:1005-1010` |
| Bleu | PWM0 ch 2 | PC20 | périph. C | — | `status = "disabled"` | observé : même fichier `:379-381`, `:992-998` |

Détails observés :
- Le nœud PWM OEM est `okay`, avec `pinctrl-0 = <0x16 0x17 0x18>`, c'est-à-dire les groupes PC10, PC11 et PC20 (`oem-rootB-kizboxmini-base.dtb.txt:815-824`, phandles `:361`, `:371`, `:381`). L'encodage `atmel,pins = <0x2 0xa 0x3 0x0>` signifie : PIO C (2), broche 10, périphérique C (3), aucune option de pull ou d'open-drain (0).
- Chaque LED utilise `pwms = <&pwm0 N 10000000 0>` : période 10 ms (100 Hz), drapeau 0 = polarité normale, `max-brightness = 255` (`:1001`, `:1007`).
- Le DTS public du noyau principal donne exactement le même câblage (`analyse-2026-11-17/buildroot-ram/boot-review/sources/torvalds__linux__arch__arm__boot__dts__microchip__at91-kizboxmini-common.dtsi:55-79` et `:93-99`). Les groupes de broches correspondent à PC10, PC11 et PC20 en périphérique C (`analyse-2026-11-17/buildroot-ram/boot-review/sources/linux-6.12/arch/arm/boot/dts/microchip/at91sam9x5.dtsi:471-474`, `:484-487`, `:497-500`).
- PC10/PC11 n'ont pas d'autre usage dans le DTB OEM. Leur seule autre fonction déclarée est ISI D10/D11 (caméra, périph. B), et ce bloc n'est pas utilisé (`oem-rootB-kizboxmini-base.dtb.txt:502-503`). Aucune propriété `gpios` ne référence PC10, PC11 ou PC20 (vérifié par recherche sur le phandle `0x27` = `gpio@fffff800` = PIO C, `:471`).

**Polarité (supposé).** Le DT ne contient ni `active-low` ni polarité inversée. Avec le pilote Atmel, la polarité normale et une luminosité de 255 donnent un rapport cyclique de 100 %, donc un niveau **haut** permanent. On en déduit LED allumée = broche à 1. Le schéma de la carte (LED directe ou transistor) n'a pas été relevé. Une observation à l'œil lors du premier essai le confirmera.

## 3. Mécanisme OEM, du démarrage à `internald`

### 3.1 Bootloader et noyaux : orange fixe

1. **K-Boot**, Linux 4.1.31 lancé par le bootstrap NAND (`analyse-2026-11-18/kboot-bootloader-sol/RAPPORT.md:11`). Le DTB annexé au volume `kboot` (offset `0x4a4848`, 25 197 octets) est **identique** au volume UBI `dtb` (vérifié par `cmp`). Son modèle est « Overkiz Kizbox Mini Mother Board » (`analyse-2026-11-19/led-etat/oem-kboot-annexe.dtb.txt:4`). Il déclare le même PWM (`:1114-1124`) et les mêmes `pwm-leds`, vert et rouge en `default-on` (`:1267-1288`). **Observé :** K-Boot démarre donc avec la LED orange.
2. K-Boot lance le noyau de la banque choisie par **`kexec`** (`analyse-2026-11-18/kboot-bootloader-sol/RAPPORT.md:18`, `:48`).
3. Le noyau KizOS 5.4.302 et son DTB `at91-kizboxmini-base.dtb` font de même, en `default-on` sur vert et rouge (`oem-rootB-kizboxmini-base.dtb.txt:990-1011`). **Observé.**
4. Le commentaire OEM résume le partage des rôles : « Bootloader, kernel and low level init are managin LEDs and then LED management is delegated to the Internal protocol » (`analyse-2026-11-17/extracted/rootB/usr/share/ui-functions.sh:17-19`).

### 3.2 Scripts shell : `led.sh` et `ui-functions.sh`

- `led.sh` écrit uniquement dans `/sys/class/leds/<type>:<couleur>:user/{trigger,brightness,pattern,control}` (`analyse-2026-11-17/extracted/rootB/usr/share/led.sh:4`, `:10-24`, `:30-45`). Par exemple, `led.sh --type pwm --leds red,green --function on` produit `echo none > trigger`, puis `echo 255 > brightness` sur chaque LED (`:263-264`).
- `ui-functions.sh` :
  - `set_led_boot` : orange fixe, rouge et vert à 100 % (`:30-36`) ;
  - `set_led_system_update` : orange en respiration à 0,5 Hz, mais **seulement pour les familles kizbox3/kizbox4**. La fonction ne fait rien sur un Kizbox Mini (`:38-44`) ;
  - `set_led_apply_update` : orange clignotant à 2 Hz, avec `blink 250` (`:58-65`).
- Appels : `kizbox-reset-factory` (`analyse-2026-11-17/extracted/rootB/etc/init.d/kizbox-reset-factory:32`, `:45-46`, `:50`, `:64`) et `wait-for-network/scripts/systemcheck` (`:48-49`, `:59`).
- `hw-default` signale des défauts en **morse rouge** : `missingsn` « ... -. », `gnlerr` « . .-. .-. », `warn` « .-- » trois fois (`analyse-2026-11-17/extracted/rootB/usr/share/hw-default:4-14`).
- **Aucun script n'utilise `ovk-gpio` pour la LED.** `ovk-gpio` ne sert qu'à PA20 (alimentation RF), PA21 (Wi-Fi), PC3 (USB), PA2…PA6 (STM32) et aux straps PC24…PC31 (section 7).

### 3.3 `internald` (Lua embarqué) : état de connexion

- La carte d'interface est choisie par son nom. Par défaut, ce nom vient de `MACHINE` (`analyse-2026-11-17/mori/internal-modules/5f01dc8891773e488bb7c703f65d745c76e6c90a9641f5d5eb4d8bf628b90868.lua:11-13`, `:26-60`). Sur ce firmware, `MACHINE=at91-kizboxmini` par défaut (`analyse-2026-11-17/extracted/rootB/usr/share/kizosenv.sh:14`). Une valeur `uiname` persistante pourrait la remplacer ; la valeur réelle sur le hub n'a pas été vérifiée.
- La définition `Boards/Definitions/at91-kizboxmini.lua` (internal 1.4.1, `appsB`, `analyse-2026-11-17/mori/internal-modules-index.json:1808-1810`) se trouve dans `analyse-2026-11-17/mori/internal-modules/cb9f16b793d96dbae8a842eb53aa3b9c50235e08e4dd8461e0c5f545577a5a0b.lua`. Elle déclare `leds = Leds({red = "pwm:red:user", green = "pwm:green:user"})` (`:18-21`).
- La bibliothèque `Overkiz.Kernel.Leds` définit les couleurs composées. `yellow` vaut `{red = 255, green = 255}`, ce qui donne la même chose que l'orange (`analyse-2026-11-17/lua/all/appsB/overkiz/lib/lua/Overkiz/Kernel/Leds.lua:22-25`). Elle passe par `Overkiz.Kernel.Led`, qui écrit dans `/sys/class/leds/<nom>/{trigger,brightness,pattern,repeat,...}` (`analyse-2026-11-17/lua/all/appsB/overkiz/lib/lua/Overkiz/Kernel/Led.lua:96-125`).

## 4. Table des états et couleurs OEM (Kizbox Mini)

| Situation | Couleur, motif | Origine | Preuve |
|---|---|---|---|
| K-Boot, puis noyau, jusqu'au lancement d'`internald` | **orange fixe** (R+V 100 %) | DT `default-on` | `oem-kboot-annexe.dtb.txt:1267-1280` ; `oem-rootB-kizboxmini-base.dtb.txt:999-1010` |
| Démarrage, réinitialisation par bouton, fin de mise à jour | orange fixe | `set_led_boot` | `ui-functions.sh:30-36` ; `kizbox-reset-factory:32,46,64` ; `systemcheck:59` |
| Application d'une mise à jour système | orange clignotant 2 Hz | `set_led_apply_update` | `ui-functions.sh:58-65` ; `systemcheck:48-49` |
| `connected` (cloud joint) | **vert fixe** | internald | `cb9f16b7…lua:63-68` |
| `connectionPending`, et `ethConnected`, qui y est ramené | **vert en respiration** (motif 0→255→0) | internald `setCycleSmoothBlink` | `cb9f16b7…lua:70-73`, `:92-96` ; `Leds.lua:121-145` |
| `disconnected`, et `ethDisconnected`, qui y est ramené | **rouge fixe** | internald | `cb9f16b7…lua:74-80`, `:92-93` |
| `localMode` | rouge fixe | internald | `cb9f16b7…lua:81-84` |
| Mise à jour du STM32 (`stm32StartUpgrade/Update`) | « jaune » (= orange) clignotant | internald `setTimerHardBlink` | `cb9f16b7…lua:102-110` ; `Leds.lua:22-25`, `:203-221` |
| Numéro de série absent, erreur générale, avertissement | rouge en morse | `hw-default` | `hw-default:4-14` |

Un minuteur de 61 s fait passer l'état à `disconnected` (rouge) quand il expire (`cb9f16b7…lua:22-28`, `:145-152`). Le décompilé ne permet pas d'établir avec certitude quel état arme ou arrête ce minuteur : les noms d'upvalues sont ambigus. Les transitions permises sont listées aux lignes `:30-61`.

## 5. Pourquoi la LED est orange en permanence sur la banque A

**Déduit, cause principale :**
1. K-Boot, toujours utilisé pour lancer la banque A (`analyse-2026-11-19/boot-banque-a/RESULTAT.md:7`), configure PWM0 ch 0 et ch 1 à 100 % sur PC10/PC11 en périphérique C. C'est l'orange (section 3.1).
2. Le passage par `kexec` ne réinitialise pas le SoC. Le contrôleur PWM et le multiplexage PIO gardent leur configuration. (**Supposé :** les pilotes `pwm-atmel` et `leds-pwm` de Linux 4.1 n'éteignent pas les canaux à l'arrêt avant `kexec`. L'orange observé par <PERSONNE> est cohérent avec ce comportement.)
3. Notre DTB `durable` ne déclare **ni `&pwm0`, ni `pwm-leds`, ni pinctrl** pour PC10/PC11/PC20 : `durable.dts:1-11` et `nand.dtsi:1-30` (`analyse-2026-11-18/persistance-banque-a/phase2/src/`), ainsi que `analyse-2026-11-17/buildroot-ram/boot-review/at91-kizboxmini-ram4.dts:34-57`, inclus par `analyse-2026-11-18/persistance-banque-a/phase2/build-kernels.sh:15-16` et `:44-47`. Dans la dtsi SoC, `pwm0` reste à `status = "disabled"` (`analyse-2026-11-17/buildroot-ram/orchestration/kernel-build-sources/arch/arm/boot/dts/microchip/at91sam9x5.dtsi:879-885`). Le pilote PWM ne se lie donc à rien, et aucun code ne touche ces broches.
4. Rien dans notre espace utilisateur ne joue le rôle d'`internald`. La LED reste donc dans l'état « démarrage » de l'OEM. Le même affichage apparaîtrait sous KizOS si `internald` ne démarrait jamais.

**Supposé, effet secondaire possible.** Sans consommateur, l'horloge périphérique PWM (PMC n° 18) peut être coupée par `clk_disable_unused` à la fin du démarrage du noyau 6.12. À 100 % de rapport cyclique, la sortie est un niveau constant, donc la couper ne change pas la couleur. Ce point n'a pas d'incidence sur les propositions ci-dessous : le pilote PWM réactive l'horloge à son attachement.

**Hypothèse écartée.** On pourrait penser aux pull-ups internes actifs au reset sur PC10/PC11 (environ 100 kΩ, **supposé** d'après la fiche SAM9G25). Ils ne suffiraient pas à donner un orange franc, et le DT K-Boot explique l'état observé sans eux. Le bootstrap NAND n'a pas été analysé pour les LED ; rien n'indique qu'il les touche.

## 6. Ce que contient notre système

| Élément | État | Preuve |
|---|---|---|
| Nœud `&pwm0` + pinctrl PC10/PC11 | **absent** | `phase2/src/durable.dts:1-11`, `nand.dtsi`, `at91-kizboxmini-ram4.dts:34-57` |
| Nœud `pwm-leds` ou `gpio-leds` | **absent** | idem |
| `CONFIG_PWM=y`, `CONFIG_PWM_ATMEL=y`, `CONFIG_PWM_ATMEL_TCB=y` | présents | `analyse-2026-11-18/persistance-banque-a/phase2/images/sam9.config:3424`, `:3426`, `:3428` |
| `CONFIG_LEDS_CLASS=y`, `CONFIG_LEDS_PWM=y`, `CONFIG_LEDS_GPIO=y` | présents | `sam9.config:2599`, `:2624`, `:2617` |
| `CONFIG_LEDS_TRIGGER_TIMER=y` | présent | `sam9.config:2656` |
| `CONFIG_LEDS_TRIGGER_DEFAULT_ON`, `CONFIG_LEDS_TRIGGER_PATTERN` | **absents** | `sam9.config:2664`, `:2673` |
| `CONFIG_GPIO_CDEV_V1=y`, pas de `GPIO_SYSFS` | conforme | `sam9.config:1646`, `:1648` |
| sysfs monté par l'init | oui | `phase2/src/init-durable:10` |

Conséquence : `linux,default-trigger = "default-on"` (DT OEM) **ne fonctionnerait pas** chez nous, faute du trigger. Il faut utiliser la propriété `default-state`. Le motif `pattern` de l'OEM n'est pas disponible non plus. Le trigger `timer` (`delay_on`, `delay_off`) l'est.

## 7. Broches à ne pas toucher

| Broche | Fonction | Preuve |
|---|---|---|
| PA0, PA1 | USART0 vers STM32 (`ttyS1`) | `…/torvalds__…at91-kizboxmini-base.dts:19-24` |
| PA2 | PWR radio (impulsion de démarrage STM32) | `analyse-2026-11-17/extracted/rootB/usr/share/stm32-utils/serial_rf:2,7` ; `analyse-2026-11-19/boot-banque-a/RESULTAT.md` |
| PA3, PA5, PA6 | TEST_RADIO, BOOT0, BOOT1 du STM32 | `serial_rf:3-5` |
| PA20 | alimentation RF | `analyse-2026-11-17/extracted/rootB/etc/init.d/rf-power:9,14,26` |
| PA21 | alimentation Wi-Fi | `…/init.d/wifi-power:9,14,26` |
| PC3 | alimentation USB | `…/init.d/usb-gpio:9-25` |
| PC16, PC17 | boutons RESET et PROG (gpio-keys) | `oem-rootB-kizboxmini-base.dtb.txt:973-989` |
| PC24…PC31 | straps de modèle, lus par K-Boot | `analyse-2026-11-17/extracted/rootB/boot/at91-kizboxmini-bootscript-vars:12-28` |
| PD4, PD5 + EBI | NAND (CS, R/B) | `phase2/src/nand.dtsi:8-9` |

PC10, PC11 et PC20 ne figurent dans aucune de ces fonctions. Ne pas toucher non plus PC20 (bleu) : il est désactivé chez l'OEM et rien ne prouve qu'un composant y soit câblé.

## 8. Propositions

### 8.1 Recommandée : nœuds DTS `pwm-leds` (DTB à reconstruire, noyau inchangé)

À ajouter, par exemple dans un nouveau `leds.dtsi` inclus par `durable.dts` (et `rescue.dts` si on le souhaite) :

```dts
&pwm0 {
	pinctrl-names = "default";
	pinctrl-0 = <&pinctrl_pwm0_pwm0_1 &pinctrl_pwm0_pwm1_1>;  /* PC10, PC11 ; pas PC20 */
	status = "okay";
};

/ {
	leds {
		compatible = "pwm-leds";
		led-green {
			label = "pwm:green:user";           /* nom identique à l'OEM */
			pwms = <&pwm0 0 10000000 0>;
			max-brightness = <255>;
			default-state = "on";               /* orange au boot = sémantique OEM */
		};
		led-red {
			label = "pwm:red:user";
			pwms = <&pwm0 1 10000000 0>;
			max-brightness = <255>;
			default-state = "on";
		};
	};
};
```

Les noms de groupes pinctrl existent dans la dtsi 6.12 (`at91sam9x5.dtsi:471`, `:484`). L'option `default-state = "keep"` est déconseillée : **supposé**, `pwm-atmel` ne sait pas relire l'état matériel, donc « keep » partirait de 0.

Utilisation depuis le service (luajit, `io.open`) ou le shell :

```sh
# vert = connecté (sémantique OEM)
echo none > /sys/class/leds/pwm:red:user/trigger;   echo 0   > /sys/class/leds/pwm:red:user/brightness
echo none > /sys/class/leds/pwm:green:user/trigger; echo 255 > /sys/class/leds/pwm:green:user/brightness
# rouge = déconnecté : inverser ; orange = les deux à 255 ; éteint = les deux à 0
# clignotement (trigger timer, disponible) :
echo timer > /sys/class/leds/pwm:green:user/trigger
echo 500 > /sys/class/leds/pwm:green:user/delay_on; echo 500 > /sys/class/leds/pwm:green:user/delay_off
```

Avantages : même interface que l'OEM, luminosité réglable de 0 à 255, clignotement géré par le noyau, aucune ligne GPIO ouverte en espace utilisateur. Coût : reconstruire le DTB `durable` et réécrire la banque A, avec la même contrainte que pour root A (`RESULTAT.md`, section « Reste à faire »). Le DTB est-il un fichier séparé ou intégré au volume root ? Cela n'a pas été vérifié ici.

### 8.2 Sans changer le DTS : GPIO chardev v1 depuis luajit

Le fichier `analyse-2026-11-19/led-etat/led-etat.lua` (**non exécuté**) suit le style de `analyse-2026-11-19/boot-banque-a/impulsion-pa2.lua` :
- il ouvre `/dev/gpiochip2` et vérifie par `GPIO_GET_CHIPINFO` que le label contient `fffff800` (PIO C) ;
- il vérifie par `GET_LINEINFO` que les lignes 10 et 11 sont libres et nommées `pioC10` et `pioC11`, ou sans nom ;
- il demande les deux lignes **en sortie** avec les niveaux voulus : vert `10`, rouge `01`, orange `11`, éteint `00`, polarité ajustable par `ON` ;
- enfin, il ferme.

Utilisation : `luajit led-etat.lua vert`.

Points **supposés**, à confirmer au premier essai :
- La demande d'une ligne en GPIO repasse la broche du périphérique C (PWM) au contrôle PIO. Le pilote `pinctrl-at91` le fait dans `gpio_request_enable`. Le PWM continue de tourner en interne, sans effet sur la broche.
- Après fermeture du descripteur, l'ABI ne garantit pas l'état de la ligne. Sur AT91, le PIO garde en pratique la dernière valeur. Si ce n'est pas le cas, le service devra garder le descripteur ouvert, ce qui permet aussi un clignotement logiciel par `SET_VALUES`.
- Le label `fffff800.gpio` et les noms `pioCnn` sont ceux de `pinctrl-at91` en 6.12. Sinon, le script refuse d'agir, ce qui est sans danger.
- Cette solution ne permet que tout-ou-rien, sans variation de luminosité. Elle devient inutilisable, et le script refuse d'agir, dès que le nœud `pwm-leds` de 8.1 existe.

### 8.3 Contrôle préalable en lecture seule (proposé, non fait)

Comme pour la lecture des lignes radio : monter `debugfs` en lecture seule, puis lire `/sys/kernel/debug/gpio` et `/sys/kernel/debug/pinctrl/*/pinmux-pins`. Le format exact n'a pas été vérifié. On s'attend à voir PC10/PC11 en « periph C » (état laissé par K-Boot) et non réclamées. Démonter ensuite.

## 9. Points non établis

- Polarité électrique réelle et schéma de la LED (non mesurés).
- Comportement exact de `kexec` sous K-Boot vis-à-vis du PWM. L'orange observé est cohérent avec « non réinitialisé », sans le prouver.
- Valeur `uiname` persistante sur le hub. Une autre définition de carte, par exemple `at91-kizboxmini-RD`, aurait une autre table de couleurs. Elle n'a pas été analysée ici.
- Rôle éventuel du bootstrap NAND sur les LED (non analysé).

## Fichiers produits

| Fichier | Rôle | SHA-256 |
|---|---|---|
| `fdtdump.py` | Décompilateur FDT minimal (Python, hors ligne), utilisé pour les deux dumps | `3dbf60d9ca72f72d0abbd67c90865481a88c34555515cc327f819f704ac828f4` |
| `oem-rootB-kizboxmini-base.dtb.txt` | Dump de `analyse-2026-11-17/extracted/rootB/boot/at91-kizboxmini-base.dtb` (SHA-256 du DTB `455927a9…a5acc`) | `e6ab39b4dc6f9b42ce3f8a43ede0d69c35c01627196fa625a291059ab25425ad` |
| `oem-kboot-annexe.dtb.txt` | Dump du DTB annexé au volume `kboot`, identique au volume `dtb` | `d586211dfc79391cea2b4b2bd540c12e556b1f78fdac99db96472f26e0e2527a` |
| `led-etat.lua` | Proposition 8.2, jamais exécutée | — |

Aucun des deux DTB ne contient d'adresse MAC ni de secret : le dumpeur masque `local-mac-address` et `mac-address`, et aucune de ces propriétés n'était présente.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
