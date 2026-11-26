set -eu
. /etc/os-release
test "$ID" = supralinux
test -d /cdrom/casper
echo '=== uptime ==='
cat /proc/uptime
echo '=== memory ==='
grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree):' /proc/meminfo
echo '=== boot ==='
systemd-analyze time || true
echo '=== load ==='
cat /proc/loadavg
echo '=== swap ==='
cat /proc/swaps
echo '=== largest RSS processes ==='
ps -eo pid,comm,rss --sort=-rss | head -n 21
echo '=== zram ==='
if test -d /sys/block/zram0; then
    cat /sys/block/zram0/disksize /sys/block/zram0/comp_algorithm
fi
