#!/usr/bin/env bash
# Point apt at another Ubuntu mirror when the runner cannot reach *.ubuntu.com (it happens: DNS outages).
#   bash .github/apt_mirrors.sh 0   -> nothing (the runner's own mirrors)
#   bash .github/apt_mirrors.sh 1   -> mirrors.edge.kernel.org
#   bash .github/apt_mirrors.sh 2   -> mirror.math.princeton.edu
set -u
case "${1:-0}" in
  1) M="http://mirrors.edge.kernel.org/ubuntu/" ;;
  2) M="http://mirror.math.princeton.edu/pub/ubuntu/" ;;
  *) exit 0 ;;
esac
for f in /etc/apt/apt-mirrors.txt /etc/apt/sources.list /etc/apt/sources.list.d/*; do
  [ -f "$f" ] || continue
  sudo sed -i -E "s#https?://[A-Za-z0-9.-]*(archive|security)\.ubuntu\.com/ubuntu/?#${M}#g; s#https?://mirrors\.edge\.kernel\.org/ubuntu/?#${M}#g; s#https?://mirror\.math\.princeton\.edu/pub/ubuntu/?#${M}#g" "$f"
done
echo "apt mirror -> $M"
grep -rh "ubuntu" /etc/apt/apt-mirrors.txt /etc/apt/sources.list.d/*.sources 2>/dev/null | head -5
