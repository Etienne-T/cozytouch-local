# Diagnostic ponctuel des bornes CETHI

L’orchestrateur exécute cette procédure une fois, après l’accord de <PERSONNE> sur l’arrêt du service, la sonde et le redémarrage. L’essai interrompt temporairement les remontées Cozytouch dans Home Assistant. Il réutilise l’application en service et limite les demandes au statut du chauffe-eau CETHI.

## 1. Vérifier l’état de départ et copier la sonde

Depuis WSL, utiliser l’alias SSH vérifié de la passerelle et adapter la variable `hub`.

```bash
hub='alias-ssh-verifie'
ssh "$hub" 'ct-update status && test -s /run/ct/healthy && cat /proc/sys/kernel/random/boot_id'
```

Conserver le mode, la version et l’identifiant de démarrage. Poursuivre si le mode est `current` ou `factory`, si `next=-` et `trying=-`, et si Home Assistant reçoit les états des deux appareils. En mode `trial`, la perte du service peut déclencher un redémarrage automatique.

```bash
script=<CHEMIN_LOCAL>
sha=81dfda97b9287180c5733e3c04733d9c34297dd21e5da6da223ee391dde86cc3
tr -d '\r' < "$script" | ssh "$hub" 'umask 077; cat > /run/ct/bornes-diag.lua'
printf '%s  /run/ct/bornes-diag.lua\n' "$sha" | ssh "$hub" 'sha256sum -c -'
```

Poursuivre uniquement si `sha256sum` annonce `OK`.

## 2. Arrêter le fils du superviseur

Dans un shell SSH root sur la passerelle, exécuter le bloc dans un sous-shell. Il identifie la commande exacte du fils et contrôle son parent via `/proc`. Le signal `TERM` laisse au service le temps de relire et de restaurer termios.

```sh
(
    set -eu
    app=$(cat /run/ct/app-dir)
    test -n "$app"
    mode=$(cat /run/ct/app-mode)
    case "$mode" in current|factory) ;; *) exit 1 ;; esac
    test -s /run/ct/healthy
    for staged in /apps/app/next /apps/app/trying; do
        if [ -e "$staged" ] || [ -L "$staged" ]; then exit 1; fi
    done
    hex() { hexdump -v -e '1/1 "%02x"' "$@"; }
    expected=$(printf 'luajit\000%s/service.lua\000--run\000' "$app" | hex)
    supervisor=$(printf '/bin/sh\000/usr/libexec/ct/supervise\000' | hex)
    children=
    for proc in /proc/[0-9]*; do
        [ "$(cat "$proc/comm" 2>/dev/null)" = luajit ] || continue
        [ "$(hex "$proc/cmdline" 2>/dev/null)" = "$expected" ] || continue
        parent=$(awk '/^PPid:/ {print $2}' "$proc/status" 2>/dev/null) || continue
        [ -n "$parent" ] || continue
        [ "$(hex "/proc/$parent/cmdline" 2>/dev/null)" = "$supervisor" ] || continue
        children="$children ${proc##*/}"
    done
    set -- $children
    [ "$#" -eq 1 ] || { printf '%s\n' 'Attendu un seul fils du superviseur'; exit 1; }
    printf 'Arrêt du fils PID %s\n' "$1"
    kill -TERM "$1"
    reste=15
    while kill -0 "$1" 2>/dev/null; do
        [ "$reste" -gt 0 ] || { printf '%s\n' 'Le fils est toujours actif'; exit 1; }
        sleep 1
        reste=$((reste - 1))
    done
)
```

Le superviseur passe en attente. Lancer la sonde seulement si le bloc a réussi. Si le fils est toujours actif, relever l’écart et arrêter l’essai.

## 3. Exécuter et collecter

Depuis WSL, dans le dossier où conserver les résultats, lancer la sonde et conserver le code de retour SSH.

```bash
ssh "$hub" 'app=$(cat /run/ct/app-dir) && test -n "$app" && LUA_PATH="$app/?.lua" luajit /run/ct/bornes-diag.lua' \
  | tee bornes-stdout.txt
diag_rc=${PIPESTATUS[0]}
printf 'code=%s\n' "$diag_rc" > bornes-retour.txt
ssh "$hub" 'cat /run/ct/bornes-diag.txt' > bornes-diag.txt
```

Conserver les trois fichiers locaux avant de redémarrer. La fenêtre de chaque demande dure 8 s et la pause entre deux demandes dure 2 s. La séquence `3, 7, 6, 7, 3` dure environ 48 s après le démarrage radio. Après un code non nul ou un écart, conserver les preuves disponibles et passer au retour en service.

Vérifier `DIAG_READY revision=2.4.2`, les cinq lignes `DIAG_WINDOW` et `DIAG_DONE restored=true`. Le champ `type` désigne la demande émise. Le champ `cethi=oui` confirme que les adresses du retour `0x010d` correspondent au chauffe-eau et au hub. Le marqueur `<ctx>` masque les dix premiers octets, les clés et adresses connues et l’adresse du dernier contrôleur dans les retours de 28 octets.

Une trame reçue pendant une pause porte `phase=pause`. Une fenêtre à `trames=0` indique un silence pendant l’observation. La valeur décodée sur 20 octets reste une lecture brute des octets 17 et 18. Vérifier le statut et la forme de la trame avant de l’interpréter. L’absence d’identifiant de type dans la réponse laisse ouverte l’attribution d’un retour tardif ou d’un doublon.

## 4. Redémarrer et vérifier la reprise

```bash
ssh "$hub" 'ct-update reboot'
# Après le retour de SSH
ssh "$hub" 'ct-update status && test -s /run/ct/healthy && cat /proc/sys/kernel/random/boot_id'
```

Vérifier que l’identifiant de démarrage a changé, que le mode et la version correspondent au relevé initial et que `/run/ct/healthy` existe à nouveau. Si la console est disponible, vérifier `STACK_START observed`, `UART_READY revision=2.4.2`, puis `HEALTH_OK counter_ack=verified`. Dans Home Assistant, vérifier la disponibilité et la réception d’états horodatés après le redémarrage pour le chauffe-eau et le sèche-serviettes.

[Sonde](../../analyse-2026-11-18/persistance-banque-a/phase2/diag/bornes-diag.lua) · SHA-256 (non publié) · Journal QEMU (non publié) · [Format des trames et limites](../parite-ha-recherche/RAPPORT.md#13-octets-uart-exacts)

> Les empreintes historiques des fichiers expurgés se rapportent aux originaux privés.
