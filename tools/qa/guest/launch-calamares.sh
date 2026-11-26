set -eu
pid=$(pgrep -u supralinux -x plasmashell | head -n 1)
test -n "$pid"
python3 - "$pid" <<'PY'
import os, subprocess, sys
from pathlib import Path
data = Path('/proc/' + sys.argv[1] + '/environ').read_bytes().split(b'\0')
session = dict(item.decode(errors='surrogateescape').split('=', 1)
               for item in data if b'=' in item)
env = {**os.environ, **{key: session[key] for key in (
    'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_RUNTIME_DIR',
    'DBUS_SESSION_BUS_ADDRESS', 'XDG_SESSION_TYPE', 'LANG') if key in session}}
env['QT_LINUX_ACCESSIBILITY_ALWAYS_ON'] = '1'
with open('/tmp/supra-qa-calamares.log', 'wb') as log:
    subprocess.Popen(['/usr/bin/calamares', '-d'], env=env,
                     stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                     start_new_session=True)
PY
