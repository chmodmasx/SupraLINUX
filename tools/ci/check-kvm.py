#!/usr/bin/env python3
"""Check actual QEMU KVM acceleration; does not boot or certify an OS."""
import json
import subprocess
import sys


def main():
    commands = ''.join(json.dumps({'execute': cmd, 'id': cmd}) + '\n'
                       for cmd in ('qmp_capabilities', 'query-kvm', 'quit'))
    try:
        result = subprocess.run([
            'qemu-system-x86_64', '-machine', 'q35,accel=kvm',
            '-m', '256', '-nodefaults', '-display', 'none', '-S',
            '-qmp', 'stdio', '-no-reboot',
        ], input=commands, text=True, capture_output=True, timeout=30)
        replies = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        kvm = next((r.get('return', {}) for r in replies if r.get('id') == 'query-kvm'), {})
        if result.returncode or not (kvm.get('present') and kvm.get('enabled')):
            raise RuntimeError(f'QMP KVM={kvm}; stderr={result.stderr.strip()}')
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f'INFRA_INVALID: {exc}', file=sys.stderr)
        return 1
    print('PASS: QEMU reports enabled KVM acceleration (infrastructure only).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
