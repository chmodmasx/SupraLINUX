#!/usr/bin/env python3
"""Generate a complete index.theme for a SupraLINUX icon theme.

The theme tree uses the Breeze layout: <context>/<size>, plus @2x/@3x
variants and optional scalable directories.  Every directory that contains
at least one icon is declared so the KDE icon loader can reach all copied
files.
"""
import argparse
import os
import re
from pathlib import Path

CONTEXTS = {
    "actions": "Actions",
    "animations": "Animations",
    "applets": "Applications",
    "apps": "Applications",
    "categories": "Categories",
    "devices": "Devices",
    "emblems": "Emblems",
    "emotes": "Emotes",
    "mimetypes": "MimeTypes",
    "places": "Places",
    "preferences": "Preferences",
    "status": "Status",
}
ORDER = list(CONTEXTS)
SCALE_RE = re.compile(r"^(?P<size>.+)@(?P<scale>[23])x$")


def icon_dirs(theme):
    found = []
    for context in ORDER:
        context_dir = theme / context
        if not context_dir.is_dir():
            continue
        for entry in sorted(context_dir.iterdir(), key=lambda item: item.name):
            if not entry.is_dir():
                continue
            if not any(entry.iterdir()):
                continue
            name = entry.name
            match = SCALE_RE.match(name)
            scale = 1
            if match:
                name = match.group("size")
                scale = int(match.group("scale"))
            if name == "scalable":
                found.append((context, "scalable", 0, scale))
            elif name.isdigit():
                found.append((context, name, int(name), scale))
            else:
                raise SystemExit(f"unexpected icon directory: {entry}")
    found.sort(key=lambda item: (
        ORDER.index(item[0]),
        1 if item[1] == "scalable" else 0,
        item[2],
        item[3],
    ))
    return found


def render(theme, name, comment):
    dirs = icon_dirs(theme)
    normal = [item for item in dirs if item[3] == 1]
    scaled = [item for item in dirs if item[3] > 1]

    lines = [
        "[Icon Theme]",
        f"Name={name}",
        f"Comment={comment}",
        "Inherits=hicolor",
        "",
        "DisplayDepth=32",
        "Example=folder",
        "FollowsColorScheme=true",
        "",
        "DesktopDefault=48",
        "DesktopSizes=16,22,32,48,64,128,256",
        "ToolbarDefault=22",
        "ToolbarSizes=16,22,32,48",
        "MainToolbarDefault=22",
        "MainToolbarSizes=16,22,32,48",
        "SmallDefault=16",
        "SmallSizes=16,22,32,48",
        "PanelDefault=48",
        "PanelSizes=16,22,32,48,64,128,256",
        "DialogDefault=32",
        "DialogSizes=16,22,32,48,64,128,256",
        "",
        "KDE-Extensions=.svg",
        "",
    ]

    def entry_name(context, size, scale):
        suffix = f"@{scale}x" if scale > 1 else ""
        return f"{context}/{size}{suffix}"

    normal_names = [entry_name(context, size, 1) for context, size, _, _ in normal]
    scaled_names = [entry_name(context, size, scale) for context, size, _, scale in scaled]
    lines.append("Directories=" + ",".join(normal_names))
    if scaled_names:
        lines.append("ScaledDirectories=" + ",".join(scaled_names))
    lines.append("")

    for context, size, numeric, scale in dirs:
        lines.append(f"[{entry_name(context, size, scale)}]")
        lines.append(f"Size={48 if size == 'scalable' else numeric}")
        if scale > 1:
            lines.append(f"Scale={scale}")
        lines.append(f"Context={CONTEXTS[context]}")
        if size == "scalable":
            lines.append("MinSize=16")
            lines.append("MaxSize=512")
            lines.append("Type=Scalable")
        else:
            lines.append("Type=Fixed")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("theme", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--comment", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    theme = args.theme.resolve()
    if not theme.is_dir():
        raise SystemExit(f"missing theme directory: {theme}")
    output = args.output or theme / "index.theme"
    output.write_text(render(theme, args.name, args.comment), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
