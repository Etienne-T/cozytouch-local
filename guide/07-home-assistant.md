# 07 · Recevoir les mesures dans Home Assistant

Le courtier et le compte dédié sont préparés avant le provisionnement en [fiche 06](06-installer-banque-a.md).

1. Dans **Paramètres → Appareils et services**, ouvrez ou ajoutez l’intégration MQTT. Indiquez votre courtier et activez la découverte MQTT. Le nom des menus peut varier selon la version.
2. Après le démarrage du service, ouvrez les appareils **Cozytouch CETHI** et **Cozytouch IC3** dans l’intégration MQTT. Contrôlez l’heure d’une mesure reçue pendant l’essai. Un ancien état conservé par le courtier ne valide pas le démarrage du jour.
3. Vérifiez la version du service. Les observations ci-dessous datent du 20 novembre 2026. La version active à cette date était la v6 `v-f871bf800c8a`. Le 25 novembre, la v8.11 pilotait aussi les deux appareils. Les séchages de 30, 60 et 120 min ont été confirmés par relecture radio et observation sur le sèche-serviettes. [Résultats par version](pilotage-et-recuperation.md)

Le 20 novembre 2026, la présence des deux appareils Cozytouch dans Home Assistant a été vérifiée après le passage à la v6. Jusqu’à la v5, Home Assistant refusait la découverte MQTT. [Rapport v6](../analyse-2026-11-20/maj-lan-6/RAPPORT.md)

| Appareil | Mesures et interprétation | Source |
| --- | --- | --- |
| CETHI, énergie | Les registres `0x0033` (appoint) et `0x0034` (PAC) sont des compteurs en Wh sur 16 bits. Ils repartent à zéro après 65 535. En v4, le total `0x0004` publié atteint 4 161 579 Wh, soit 2 487 Wh de plus que le relevé Overkiz du 19 novembre. La hausse correspond à celle de l’index PAC sur cet intervalle. | [Rapport v3](../analyse-2026-11-20/maj-lan-3/RAPPORT.md) · [Rapport v4](../analyse-2026-11-20/maj-lan-4/RAPPORT.md) |
| CETHI, consigne | Le diagnostic matériel a lu des bornes de 20 et 62 °C. La v4 avait retiré les demandes de bornes du service. La v5 lance au plus une série de lectures des bornes par session. Elle calcule la consigne si la série est valide. Le relevé MQTT v5 donne 62 °C pour la cible brute 51 200 et publie les deux bornes. | [Diagnostic des bornes](../analyse-2026-11-20/diag-bornes/RESULTAT.md) · [Rapport v4](../analyse-2026-11-20/maj-lan-4/RAPPORT.md) · [Rapport v5](../analyse-2026-11-20/maj-lan-5/RAPPORT.md) |
| IC3, boost et séchage | Les registres `0x013a` et `0x013c` indiquent les durées restantes. Le réglage du boost `0x013b` valait 20 min en v3. Le réglage du séchage `0x013d` valait 90 min en v4 et en v5. Le maximum lu en v4 était de 120 min. | [Rapport v3](../analyse-2026-11-20/maj-lan-3/RAPPORT.md) · [Rapport v4](../analyse-2026-11-20/maj-lan-4/RAPPORT.md) · [Rapport v5](../analyse-2026-11-20/maj-lan-5/RAPPORT.md) |
| IC3, température ambiante | Le registre `0x0115` a donné 18,5 °C en v4 et 17,75 °C en v5. | [Rapport v4](../analyse-2026-11-20/maj-lan-4/RAPPORT.md) · [Rapport v5](../analyse-2026-11-20/maj-lan-5/RAPPORT.md) |

Le relevé MQTT après promotion v5 compte 21 composants de découverte par appareil. Le service lit les équipements et publie leurs états. Les relevés ne comportent aucune écriture de réglage. [Rapport v5](../analyse-2026-11-20/maj-lan-5/RAPPORT.md)

## Écarts et limites

- L’échelle du V40 (`0x0031`) reste inconnue. Utilisez la valeur brute. Les relevés du 19 et du 20 novembre montrent un écart pour le compteur PAC. La hausse du total sur cet intervalle correspond à la hausse du compteur PAC. Les rapports ne présentent pas de comparaison simultanée qui lève l’écart avec la référence. [Rapport v3](../analyse-2026-11-20/maj-lan-3/RAPPORT.md) · [Rapport v4](../analyse-2026-11-20/maj-lan-4/RAPPORT.md) · [Relevé v2](../analyse-2026-11-20/maj-lan-2/PROCEDURE.md)
- Les champs du mode manuel issus de `0x0041` étaient nuls lors du relevé v4. Les bornes de la consigne v5 viennent de demandes de statut étendu distinctes. [Rapport v4](../analyse-2026-11-20/maj-lan-4/RAPPORT.md) · [Diagnostic des bornes](../analyse-2026-11-20/diag-bornes/RESULTAT.md)
- L’IC3 a renvoyé `04af` pour `0x0116`. L’hypothèse d’un compteur de consommation reste à confirmer. Les quatre diagnostics d’environnement `env_*` sont désactivés par défaut en v5 après les valeurs suspectes observées en v4. Le service continue de lire `0x0140`. [Rapport v4](../analyse-2026-11-20/maj-lan-4/RAPPORT.md) · [Rapport v5](../analyse-2026-11-20/maj-lan-5/RAPPORT.md)
- Astra signale un risque résiduel pour la consigne affichée. Une ancienne réponse pourrait être acceptée pendant la fenêtre exacte d’une demande de borne basse restée sans réponse. Le diagnostic matériel n’a observé aucun doublon ni retard de ce type. [Seconde revue Astra](../analyse-2026-11-20/maj-lan-5/REVUE-ASTRA-2.md) · [Diagnostic des bornes](../analyse-2026-11-20/diag-bornes/RESULTAT.md)

La compatibilité avec d’autres appareils io-homecontrol reste à tester.

[Précédente](06-installer-banque-a.md) · [Sommaire](README.md#sommaire) · [Suivante](08-mises-a-jour-et-retour.md)
