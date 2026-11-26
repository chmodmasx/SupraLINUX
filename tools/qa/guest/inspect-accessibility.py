"""Read Calamares accessibility controls through the live session's AT-SPI bus.

Run inside the disposable live guest as its desktop user. Does not interact
with controls, modify partitions, or require extra installed Python packages.
"""
import argparse
import ast
import json
import re
import subprocess
import time


ROOT = "/org/a11y/atspi/accessible/root"
REGISTRY = "org.a11y.atspi.Registry"
ACCESSIBLE = "org.a11y.atspi.Accessible"
PROPERTIES = "org.freedesktop.DBus.Properties"


def parse_refs(raw):
    # gdbus prints GVariant objectpath annotations on the first array element.
    value = ast.literal_eval(re.sub(r"\bobjectpath\s+(?=['\"])", "", raw.strip()))
    if not isinstance(value, tuple) or len(value) != 1 or not isinstance(value[0], list):
        raise ValueError("Unexpected accessibility children response")
    refs = value[0]
    if any(not isinstance(ref, tuple) or len(ref) != 2 or
           not all(isinstance(item, str) for item in ref) or
           not ref[1].startswith("/") for ref in refs):
        raise ValueError("Invalid accessibility object reference")
    return refs


def parse_string(raw):
    match = re.fullmatch(r"\(\s*<(.*)>\s*,\s*\)", raw.strip())
    value = ast.literal_eval(match[1]) if match else ast.literal_eval(raw.strip())[0]
    if not isinstance(value, str):
        raise ValueError("Expected accessibility string")
    return value


class Bus:
    def __init__(self, deadline):
        self.deadline = deadline
        raw = self.command("gdbus", "call", "--session", "--dest", "org.a11y.Bus",
                           "--object-path", "/org/a11y/bus",
                           "--method", "org.a11y.Bus.GetAddress")
        self.address, = ast.literal_eval(raw.strip())
        if not self.address.startswith("unix:"):
            raise ValueError("Expected local AT-SPI Unix socket")

    def command(self, *args):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Accessibility probe deadline exceeded")
        return subprocess.check_output(args, text=True, stderr=subprocess.PIPE,
                                       timeout=min(3, remaining))

    def call(self, ref, method, *args):
        return self.command("gdbus", "call", "--address", self.address,
                            "--dest", ref[0], "--object-path", ref[1],
                            "--method", method, *args)

    def children(self, ref):
        return parse_refs(self.call(ref, ACCESSIBLE + ".GetChildren"))

    def name(self, ref):
        return parse_string(self.call(ref, PROPERTIES + ".Get", ACCESSIBLE, "Name"))

    def role(self, ref):
        return parse_string(self.call(ref, ACCESSIBLE + ".GetRoleName"))


def inspect(bus, limit=160):
    apps = []
    matches = []
    for ref in bus.children((REGISTRY, ROOT)):
        try:
            name = bus.name(ref)
            apps.append({"name": name, "ref": ref})
            if "calamares" in name.casefold():
                matches.append(ref)
        except (subprocess.SubprocessError, ValueError, TimeoutError) as exc:
            apps.append({"ref": ref, "error": str(exc)})
    report = {"applications": apps, "nodes": [], "status": "BLOCKED"}
    if len(matches) != 1:
        report["error"] = "Calamares application root missing or ambiguous"
        return report
    queue = [(matches[0], None, 0)]
    seen = set()
    while queue and len(seen) < limit:
        ref, parent, depth = queue.pop(0)
        if ref in seen or depth > 12:
            continue
        seen.add(ref)
        node = {"ref": ref, "parent": parent, "depth": depth}
        report["nodes"].append(node)
        try:
            node["name"] = bus.name(ref)
            node["role"] = bus.role(ref)
            queue.extend((child, ref, depth + 1) for child in bus.children(ref))
        except (subprocess.SubprocessError, ValueError, TimeoutError) as exc:
            node["error"] = str(exc)
            if isinstance(exc, TimeoutError):
                report["error"] = str(exc)
                break
    report["truncated"] = bool(queue)
    if report["nodes"] and not report.get("error"):
        report["status"] = "PASS"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=160)
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()
    if not 1 <= args.limit <= 512 or not 1 <= args.timeout <= 120:
        parser.error("Bounded limit and timeout required")
    try:
        report = inspect(Bus(time.monotonic() + args.timeout), args.limit)
    except (OSError, ValueError, TimeoutError, subprocess.SubprocessError) as exc:
        report = {"status": "BLOCKED", "error": str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
