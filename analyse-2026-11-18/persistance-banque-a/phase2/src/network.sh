#!/bin/sh
set -eu
lan=$1 prefix=$2 broker=$3 port=$4 admin=$5
test "$#" -eq 5
filter() {
    iptables -w "$@"
}
# Init has installed DROP on all chains and disabled IPv6 before this script.
filter -A OUTPUT -o lo -j ACCEPT
filter -A INPUT -i lo -j ACCEPT
filter -A OUTPUT -o eth0 -s "$lan" -d "$broker" -p tcp --dport "$port" \
    -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
filter -A INPUT -i eth0 -s "$broker" -d "$lan" -p tcp --sport "$port" \
    -m conntrack --ctstate ESTABLISHED -j ACCEPT
filter -A INPUT -i eth0 -s "$admin" -d "$lan" -p tcp --dport 2222 \
    -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
filter -A OUTPUT -o eth0 -s "$lan" -d "$admin" -p tcp --sport 2222 \
    -m conntrack --ctstate ESTABLISHED -j ACCEPT
ip addr add "$lan/$prefix" dev eth0
ip link set lo up
ip link set eth0 up
printf '%s\n' CONFINED_LAN_UP
