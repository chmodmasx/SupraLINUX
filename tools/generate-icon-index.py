#!/usr/bin/env python3
"""Generate an index.theme that behaves like the Breeze reference theme.

The theme tree is a complete copy of Breeze (or Breeze Dark), but Breeze's
index.theme intentionally hides some directories and marks many of the
remaining ones as scalable.  Declaring every directory as fixed changes icon
lookup: at a non-native size the loader cannot use a fixed directory and falls
back to another theme, which is how colourful preference icons turn into
monochrome symbolic ones.  Copy the reference metadata instead and only add
the SupraLINUX branding directories that the reference does not have.
"""
import argparse
import configparser
from pathlib import Path

# Directories that only exist in the SupraLINUX branding (start-here and
# kickoff aliases).  Breeze does not need them, but the branding does.
EXTRAS = {
    "applets/32": {"Size": "32", "Context": "Status", "Type": "Fixed"},
    "applets/96": {"Size": "96", "Context": "Status", "Type": "Fixed"},
    "applets/512": {"Size": "512", "Context": "Status", "Type": "Fixed"},
    "applets/scalable": {
        "Size": "48", "Context": "Status", "MinSize": "16",
        "MaxSize": "512", "Type": "Scalable",
    },
    "places/128": {"Size": "128", "Context": "Places", "Type": "Fixed"},
    "places/256": {"Size": "256", "Context": "Places", "Type": "Fixed"},
    "places/512": {"Size": "512", "Context": "Places", "Type": "Fixed"},
    "places/scalable": {
        "Size": "48", "Context": "Places", "MinSize": "16",
        "MaxSize": "512", "Type": "Scalable",
    },
}

IDENTITY_KEYS = [
    "DisplayDepth", "Example", "FollowsColorScheme",
    "DesktopDefault", "DesktopSizes", "ToolbarDefault", "ToolbarSizes",
    "MainToolbarDefault", "MainToolbarSizes", "SmallDefault", "SmallSizes",
    "PanelDefault", "PanelSizes", "DialogDefault", "DialogSizes",
    "KDE-Extensions",
]


def read_index(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return parser


def has_icons(theme, name):
    directory = theme / name
    return directory.is_dir() and any(directory.iterdir())


def render(theme, name, comment, reference):
    reference_parser = read_index(reference)
    index = reference_parser["Icon Theme"]
    reference_dirs = [item for item in index["Directories"].split(",") if item]
    reference_scaled = [item for item in index.get("ScaledDirectories", "").split(",") if item]

    directories = [item for item in reference_dirs if has_icons(theme, item)]
    scaled = [item for item in reference_scaled if has_icons(theme, item)]
    for extra, metadata in EXTRAS.items():
        if not has_icons(theme, extra):
            continue
        # ScaledDirectories is only for @2x/@3x variants. A scalable SVG
        # directory (places/scalable) remains a normal scale-1 directory.
        directories.append(extra)

    lines = [
        "[Icon Theme]",
        f"Name={name}",
        f"Comment={comment}",
        "Inherits=hicolor",
        "",
    ]
    for key in IDENTITY_KEYS:
        if key in index:
            lines.append(f"{key}={index[key]}")
    lines.append("")
    lines.append("Directories=" + ",".join(directories))
    if scaled:
        lines.append("ScaledDirectories=" + ",".join(scaled))
    lines.append("")

    for entry in directories + scaled:
        section = dict(reference_parser[entry]) if reference_parser.has_section(entry) else {}
        section = section or EXTRAS[entry]
        lines.append(f"[{entry}]")
        for key in ["Size", "Scale", "Context", "Type", "MinSize", "MaxSize", "Threshold"]:
            if key in section:
                lines.append(f"{key}={section[key]}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("theme", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--comment", required=True)
    parser.add_argument("--reference", required=True, type=Path,
                        help="index.theme of the Breeze theme this copy is based on")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    theme = args.theme.resolve()
    if not theme.is_dir():
        raise SystemExit(f"missing theme directory: {theme}")
    output = args.output or theme / "index.theme"
    output.write_text(render(theme, args.name, args.comment, args.reference), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
