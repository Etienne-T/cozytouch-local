# Accès administrateur — état réseau du 17 novembre 2026

<PERSONNE> a autorisé les tests réseau du hub et la recherche d’un accès administrateur réversible. Les opérations décrites ici n’envoient aucun ordre aux appareils, ne contactent pas le cloud et ne modifient pas la NAND.

## État constaté

À 15:38 UTC, depuis le HP, l’ancienne adresse `<IP_HUB>` ne répond pas et la résolution ARP termine en `FAILED`. Une découverte ARP Windows, entre 15:40:35 et 15:41:07 UTC sur `<RESEAU_LOCAL>`, n’a trouvé aucune adresse correspondant exactement à la MAC enregistrée dans le volume `security` de la NAND. La même adresse est `Unreachable` dans la table des voisins Windows à 15:41 UTC. La MAC complète n’est pas reproduite dans cette note.

L’absence de réponse a été levée après le redémarrage électrique effectué par <PERSONNE>. À 15:43:16 UTC, l’adresse `<IP_HUB>` correspond à la MAC attendue. Les 17 ports usuels et natifs testés sont fermés. Entre 15:43:39 et 15:43:48 UTC, les 65 535 ports TCP répondent par refus de connexion : aucun port ouvert ou délai dépassé dans ce passage. Aucun essai d’authentification n’a été tenté. Les deux questions mDNS unicast `_kizbox._tcp.local` et `_kizboxdev._tcp.local` restent sans réponse à 15:45 UTC ; cela ne prouve pas l’absence de toute annonce multicast.

L’acquisition JTAG précédente avait utilisé la RAM ; `jtag/ACQUISITION.md` précisait qu’un redémarrage électrique était nécessaire pour reprendre un fonctionnement normal. Le retour réseau après ce redémarrage est cohérent avec cette explication. Cet agent ne commande ni JTAG ni GPIO et n’a pas redémarré le matériel.

## Tests préparés

Après le signal du coordinateur indiquant le lancement du noyau RAM à 16:28:55 UTC, deux contrôles ciblés ont été effectués depuis le HP : à 16:29:18.785 UTC et à 16:30:15.035 UTC. Dans les deux cas, la MAC du voisin correspond exactement à la référence NAND. Les ports 2222, 22, 443 et 8443 refusent tous la connexion (errno 111). Aucune clé d’hôte n’a donc pu être récupérée et aucune authentification n’a été tentée. Les contrôles se sont arrêtés après ce deuxième passage, conformément au périmètre demandé.

Ces refus ne permettent pas, à eux seuls, de distinguer un retour au noyau NAND, un wrapper non exécuté ou un délai dans le wrapper. Celui-ci attend notamment le marqueur natif `/tmp/boot`, puis la génération d’une clé RSA avant de lancer le serveur. La lecture matérielle de la ligne de commande active et, si accessible, l’état des processus doivent trancher. Preuves : `post-ram-network-20261117T162918Z.json` et `post-ram-network-20261117T163015Z.json`.

Sur un nouveau signal explicite du coordinateur, un dernier contrôle à 16:35:39.290 UTC confirme la même identité MAC et les mêmes quatre refus TCP, plus de six minutes après le signal de démarrage RAM. Aucune clé d’hôte n’a été récupérée et aucune authentification n’a été tentée. Le passage réseau est clos en attente du diagnostic matériel. Preuve : `post-ram-network-20261117T163539Z.json`.

Le coordinateur a ensuite confirmé le retour au démarrage normal par la routine SRAM et le reset logiciel, puis l’arrêt d’OpenOCD et le passage des GPIO JTAG en entrées. Le contrôle réseau final à 16:41:07.560 UTC retrouve le hub à `<IP_HUB>` avec sa MAC exacte. Les ports 2222, 22, 443 et 8443 refusent la connexion. **Aucun accès SSH n’a été obtenu ; le retour réseau après reset normal est vérifié. Le fonctionnement du cloud et des appareils reste non vérifié.** Aucun nouvel essai ni activation n’a suivi. Preuve finale : `after-normal-reset-20261117T164107Z.json` ; le fichier source HP conserve le nom `post-ram-network-20261117T164107Z.json` utilisé par le script générique.

`discover-hub.ps1` recherche uniquement la MAC connue par ARP sur le LAN. Il ne teste pas les services des autres appareils.

`probe-hub.py` exige que le voisin Linux porte la MAC attendue avant tout test TCP. Sans correspondance, il enregistre l’échec d’identité et n’interroge aucun port. Avec correspondance, il teste les ports natifs attendus et quelques services LAN usuels. Une option distincte permet une découverte TCP complète. Il ne tente aucun mot de passe ou clé.

Le script et la référence de MAC sont prêts sur le HP, dans `<CHEMIN_LOCAL>`. Les essais suivants commenceront par la vérification d’identité. Si un service SSH répond, son empreinte publique devra être comparée à la clé d’hôte sauvegardée avant toute authentification. Les appels d’API seront limités à l’identification et à la lecture.

## Réversibilité

Aucun compte, jeton, clé autorisée, service ou fichier du hub n’a été changé par cette piste. Le retour arrière réseau est donc sans action sur le hub. Une activation ultérieure devra conserver une trace précise des fichiers ou processus ajoutés et leur révocation. Les commandes de changement de mode, d’actionnement radio, de réinitialisation et de mise à jour ne font pas partie de ces tests.

Preuves : `arp-discovery.json`, `initial-probe.json`, `after-powercycle-known-ports.json`, `after-powercycle-full-tcp.json`, `after-powercycle-mdns.json` et scripts conservés dans ce dossier. Aucun accès administrateur obtenu par cette piste réseau. La suite doit établir une activation temporaire par un autre canal, puis vérifier le nouvel accès.

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
