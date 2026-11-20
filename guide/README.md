# Lecture locale depuis Home Assistant · Retour d’expérience sur un bridge Cozytouch

Ce parcours s’adresse au propriétaire d’un Atlantic 500090 qui sait mesurer une tension, identifier des broches et administrer Linux et MQTT. Sur le bridge essayé, Linux 6.12 en banque A lit le chauffe-eau CETHI et le sèche-serviettes IC3 par le contrôleur radio d’origine. Il publie leurs états sur le réseau local. La banque A ne fournit plus le cloud Overkiz ni l’application Cozytouch. La banque B conserve le système constructeur.

**Avant d’ouvrir le boîtier**, prévoyez comment assurer le chauffage et l’eau chaude pendant l’intervention. Le hub participe à leur pilotage. Une erreur de câblage ou d’écriture peut rendre le bridge inutilisable. La banque B sert de secours si le chargeur, la NAND et la sélection de banque fonctionnent encore. Vous assumez l’intervention sur votre matériel.

**Durée.** Les acquisitions et essais documentés couvrent les 17 au 20 novembre 2026. Le temps nécessaire à une seconde personne n’a pas été mesuré. Prévoyez plusieurs séances et une interruption dont la durée peut dépasser celle du montage.

**Contextes radio à vérifier avant d’ouvrir le boîtier.** Le parcours couvre les appareils déjà associés pour lesquels vous disposez des contextes radio propres à votre installation. Vérifiez que vous pouvez identifier chaque cible et renseigner son entrée dans `targets.conf` au format attendu en fiche 06. Une sauvegarde NAND ou une connexion SSH réussie ne prouve pas que ces données sont disponibles. Si elles manquent, arrêtez ici. Aucun parcours d’association sur une seconde installation n’est validé.

**Point d’arrêt avant la bascule en banque A.** Le retour applicatif change la version du service en A. La sélection de B dépend du chargeur et des volumes B intacts. Le scénario de récupération du pointeur B est simulé. Sans récupération matérielle qualifiée pour votre carte, gardez B sélectionnée. La restauration intégrale de la NAND reste non testée.

~~~mermaid
flowchart TD
 M[01 Identifier la carte] --> N[02 Vérifier la NAND]
 N --> R[03 Linux temporaire et SSH]
 R --> S[04 Vérifier la flash radio]
 S --> C[05 Préparer les images]
 C --> A[06 Préparer MQTT et provisionner A]
 A --> Q{Récupération matérielle qualifiée ?}
 Q -->|Non| X[Arrêt en B]
 Q -->|Oui| V[Sélectionner A après relectures]
 V --> H[07 Vérifier les mesures dans HA]
 H --> U[08 Mettre à jour ou revenir en arrière]

~~~

Suivez les fiches 01 à 08 dans cet ordre. La fiche 03 décrit la séquence de démarrage d’un Linux temporaire en RAM par JTAG, telle qu’elle a ouvert un SSH root sur notre carte les 17 et 19 novembre 2026. Les adresses, le noyau et les straps y sont propres à notre matériel : le lecteur les réétablit pour le sien, et plusieurs étapes restent des transpositions non testées vers une autre carte. Consultez [le dépannage](09-depannage.md) au premier écart.

Les mentions **vérifié** concernent un seul bridge à la date indiquée. Toute instruction adressée au lecteur constitue une **transposition non testée sur son matériel**. Les noms entre chevrons désignent vos valeurs. Gardez vos sauvegardes, clés et paramètres radio hors des dossiers partagés.

## Sommaire

- [01 · Reconnaître la carte et câbler la sonde](01-materiel.md)
- [02 · Sauvegarder les pages et leurs octets auxiliaires](02-sauvegarde-nand.md)
- [03 · Démarrer un Linux temporaire par JTAG et ouvrir SSH](03-jtag-vers-ssh.md)
- [04 · Sauvegarder le contrôleur radio](04-sauvegarde-stm32.md)
- [05 · Préparer Linux v4](05-construire-v4.md)
- [06 · Préparer la banque inactive et vérifier le premier démarrage](06-installer-banque-a.md)
- [07 · Recevoir les mesures dans Home Assistant](07-home-assistant.md)
- [08 · Mettre à jour ou revenir en arrière](08-mises-a-jour-et-retour.md)
- [09 · S’arrêter au premier écart](09-depannage.md)
- [Sources et portée des preuves](REFERENCES.md)
