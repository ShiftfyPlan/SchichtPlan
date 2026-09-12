#!/usr/bin/env python3
"""Design-token drift audit (Phase 0, 2026-09-05).

Counts every hardcoded styling decision in the UI and compares it against the
tokens already defined in globals.css. Read-only: touches nothing.

    python3 scripts/ui-audit.py            # summary to stdout
    python3 scripts/ui-audit.py --json out.json

Baseline recorded 2026-09-05 (589 files):
    11,410 hardcoded colour utilities, 444 distinct
    21 / 589 files reference brand tokens (3.6%)
    20 colour families; 4 neutral ramps (gray/zinc/neutral/slate) = 7,028 utils
    204 spacing values, 11 radii, 10 font sizes, 127 arbitrary [..] values
    dark-mode coverage 50%; 309 <button>, 19 with an accessible name (6%)

Re-run after any token work; every number should fall.
"""
import re, os, json, sys, collections

ROOTS = ["src/app", "src/components"]
PALETTES = ("slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|"
            "emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose")

color_re = re.compile(
    rf"\b(bg|text|border|ring|from|to|via|fill|stroke|divide|shadow|outline|decoration|accent)"
    rf"-({PALETTES})-(\d{{2,3}})\b")
arb_re    = re.compile(r"\[[^\]\s]{2,40}\]")
space_re  = re.compile(r"\b(p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|gap-x|gap-y|space-x|space-y)-(\[?[\w./]+\]?)\b")
font_re   = re.compile(r"\btext-(xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl|\[[^\]]+\])\b")
radius_re = re.compile(r"\brounded(-[a-z0-9]+)?\b")
token_re  = re.compile(r"var\(--brand|--color-|bg-brand|text-brand")


def collect():
    files = []
    for root in ROOTS:
        for dp, _, fns in os.walk(root):
            if "__tests__" in dp:
                continue
            for f in fns:
                if f.endswith((".tsx", ".ts")):
                    files.append(os.path.join(dp, f))
    return sorted(files)


def main():
    files = collect()
    colors = collections.Counter(); families = collections.Counter()
    spacing = collections.Counter(); fonts = collections.Counter()
    radii = collections.Counter(); arbitrary = collections.Counter()
    per_file = collections.Counter(); token_users = set()
    dark_gaps = []; total_light = total_dark = 0
    buttons = labelled = 0

    for p in files:
        s = open(p, encoding="utf-8", errors="ignore").read()

        hits = color_re.findall(s)
        for prefix, fam, shade in hits:
            colors[f"{prefix}-{fam}-{shade}"] += 1
            families[fam] += 1
        if hits:
            per_file[p] = len(hits)

        for m in arb_re.findall(s):
            if any(k in m for k in ("px", "rem", "#", "%", "vh", "vw", "calc", "fr")):
                arbitrary[m] += 1
        for a, b in space_re.findall(s):
            spacing[f"{a}-{b}"] += 1
        for f_ in font_re.findall(s):
            fonts[f"text-{f_}"] += 1
        for r_ in radius_re.findall(s):
            radii["rounded" + (r_ or "")] += 1
        if token_re.search(s):
            token_users.add(p)

        if p.endswith(".tsx"):
            light = len(re.findall(r'(?<!dark:)\b(?:bg|text|border)-(?:%s)-\d{2,3}' % PALETTES, s))
            dark = len(re.findall(r'dark:(?:bg|text|border)-(?:%s)-\d{2,3}' % PALETTES, s))
            total_light += light; total_dark += dark
            if light >= 15 and dark / max(light, 1) < 0.25:
                dark_gaps.append((round(100 * dark / light), light, dark, p))
            for tag in re.findall(r"<button\b[^>]*>", s):
                buttons += 1
                if "aria-label" in tag:
                    labelled += 1

    neutrals = {k: v for k, v in families.items()
                if k in ("gray", "zinc", "neutral", "slate", "stone")}
    dark_gaps.sort()

    report = {
        "files_scanned": len(files),
        "total_color_utils": sum(colors.values()),
        "distinct_color_utils": len(colors),
        "files_using_brand_tokens": len(token_users),
        "color_families": families.most_common(),
        "neutral_ramps": neutrals,
        "neutral_ramp_total": sum(neutrals.values()),
        "top_colors": colors.most_common(25),
        "distinct_spacing": len(spacing),
        "distinct_font_sizes": len(fonts),
        "distinct_radii": len(radii),
        "radii": radii.most_common(),
        "arbitrary_values": len(arbitrary),
        "dark_coverage_pct": round(100 * total_dark / max(total_light, 1)),
        "dark_gap_files": dark_gaps[:20],
        "buttons": buttons,
        "buttons_labelled": labelled,
        "worst_files": per_file.most_common(15),
    }

    if "--json" in sys.argv:
        dest = sys.argv[sys.argv.index("--json") + 1]
        json.dump(report, open(dest, "w"), indent=1)
        print(f"wrote {dest}")

    r = report
    print(f"files scanned              : {r['files_scanned']}")
    print(f"hardcoded colour utilities : {r['total_color_utils']} ({r['distinct_color_utils']} distinct)")
    print(f"files using brand tokens   : {r['files_using_brand_tokens']}")
    print(f"neutral ramps in use       : {len(neutrals)} -> {r['neutral_ramp_total']} utilities")
    for fam, n in sorted(neutrals.items(), key=lambda x: -x[1]):
        print(f"    {fam:<8} {n}")
    print(f"colour families            : {len(r['color_families'])}")
    print(f"distinct spacing values    : {r['distinct_spacing']}")
    print(f"distinct font sizes        : {r['distinct_font_sizes']}")
    print(f"distinct radii             : {r['distinct_radii']}")
    print(f"arbitrary [..] values      : {r['arbitrary_values']}")
    print(f"dark-mode coverage         : {r['dark_coverage_pct']}%")
    print(f"buttons with aria-label    : {labelled}/{buttons}")
    print("\nworst files:")
    for f, n in r["worst_files"][:10]:
        print(f"   {n:>4}  {f}")
    print("\nlowest dark coverage:")
    for pct, light, dark, p in r["dark_gap_files"][:10]:
        print(f"   {pct:>3}%  light={light:<4} dark={dark:<4} {p}")


if __name__ == "__main__":
    main()
