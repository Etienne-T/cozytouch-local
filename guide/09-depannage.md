# 09 · S’arrêter au premier écart

| Observation | Vérification suivante | Condition de reprise |
|---|---|---|
| TAP absent ou capture IR incorrecte | Couper, revoir l’orientation, le contact de masse et la tension. Vérifier la disponibilité des GPIO. | IDCODE attendu et scan stable. |
| Un lot NAND diverge | Garder les deux résultats. Vérifier le transfert, les contacts et la vitesse de la sonde. | Seconde lecture indépendante conforme sur les 64 lots. |
| Redémarrage pendant le transfert RAM | Examiner le journal du watchdog et la durée du transfert. | Fenêtre de travail validée pour cette image. |
| Console DBGU muette | Examiner les autres preuves de démarrage de l’image. Le silence de la console ne suffit pas à diagnostiquer un blocage. | Journal ou session identifiée confirmant le stade atteint. |
| Démarrage imprévisible | Comparer les tailles réelles, les zones chargées et l’espace de décompression avec le plan de l’image. | Absence de recouvrement vérifiée pour cette image. |
| SSH tarde à apparaître | Vérifier la progression locale. Une génération de clé RSA sur ARM9 peut être lente. | Serveur prêt et identité connue. |
| SSH expire après redémarrage | Contrôler le poste source autorisé et l’entrée de voisinage pour `<IP_HUB>`. Une MAC aléatoire peut laisser une ancienne entrée ARP. | Correspondance actuelle confirmée et identité SSH vérifiée. |
| Alerte de clé d’hôte, RAM03 | Comparer avec une référence indépendante, propre au démarrage courant. RAM03 régénère sa clé à chaque démarrage. | Arrêt en cas de discordance. Reprendre uniquement après concordance vérifiée. |
| Alerte de clé d’hôte, banque A | Comparer avec la référence conservée au provisionnement. | Arrêt en cas de discordance. Reprendre uniquement après concordance vérifiée. |
| LED verte mais valeur HA ancienne | Vérifier la version de l’application, la disponibilité du courtier et l’heure de réception. | Nouvelle lecture reçue pour chaque appareil attendu. |
| Valeur V40 ou PAC surprenante | Conserver la grandeur brute. Voir les écarts dans la fiche 07. | Unité ou conversion qualifiée avant usage dans un calcul. |

[Précédente](08-mises-a-jour-et-retour.md) · [Sommaire](README.md#sommaire) · [Suivante](REFERENCES.md)
