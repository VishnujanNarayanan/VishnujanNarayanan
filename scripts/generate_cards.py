#!/usr/bin/env python3
"""Generate self-hosted GitHub stat + contribution SVG cards.

Fetches live data from the GitHub GraphQL API and renders light/dark SVG cards
into assets/. Self-hosted on purpose: the popular third-party card services
(github-readme-stats, github-profile-trophy) run on free Vercel quotas that go
down, which leaves a profile README full of broken images.

Auth: reads GITHUB_TOKEN from the environment, else falls back to `gh auth token`.
Usage: python3 scripts/generate_cards.py [username]
"""

from __future__ import annotations

import bisect
import datetime as dt
import json
import os
import random
import subprocess
import sys
import urllib.request
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else "VishnujanNarayanan"
OUT = Path(__file__).resolve().parent.parent / "assets"

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    login
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

THEMES = {
    "light": {
        "text": "#24292f",
        "muted": "#57606a",
        "accent": "#0969da",
        "card": "#ffffff",
        "border": "#d0d7de",
        "track": "#eaeef2",
        "heat": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "snake_head": "#8250df",
        "snake_body": "#a475f9",
    },
    "dark": {
        "text": "#c9d1d9",
        "muted": "#8b949e",
        "accent": "#58a6ff",
        "card": "#0d1117",
        "border": "#30363d",
        "track": "#21262d",
        "heat": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
        "snake_head": "#bc8cff",
        "snake_body": "#a371f7",
    },
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Snake animation.
SNAKE_STEP_SECONDS = 0.03    # one grid step per frame
SNAKE_LENGTH = 4             # starting length, and the length it returns to
GROW_PER_CELLS = 10          # cells swallowed per extra body segment
DETOUR_CHANCE = 0.25         # how often the head wanders off the direct line
HUNT_SEED = 7                # fixed, so output only changes with the data


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    return subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True
    ).stdout.strip()


def fetch(login: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token()}",
            "Content-Type": "application/json",
            "User-Agent": f"{login}-profile-cards",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def human(n: int) -> str:
    if n >= 1000:
        trimmed = f"{n / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{trimmed}k"
    return str(n)


def collect(user: dict) -> dict:
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]

    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])

    # Streaks over the trailing-year window. A zero-contribution *today* does
    # not break the current streak (it isn't over yet) -- GitHub's convention.
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        longest = max(longest, run)

    current = 0
    today = dt.date.today().isoformat()
    for d in reversed(days):
        if d["contributionCount"] > 0:
            current += 1
        elif d["date"] == today:
            continue
        else:
            break

    langs: dict[str, dict] = {}
    stars = 0
    for repo in user["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            entry = langs.setdefault(
                name, {"size": 0, "color": edge["node"]["color"] or "#8b949e"}
            )
            entry["size"] += edge["size"]
    total_size = sum(v["size"] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1]["size"])[:6]

    return {
        "name": user["name"] or user["login"],
        "login": user["login"],
        "weeks": cal["weeks"],
        "total": cal["totalContributions"],
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "repos": user["repositories"]["totalCount"],
        "stars": stars,
        "followers": user["followers"]["totalCount"],
        "current": current,
        "longest": longest,
        "langs": [
            (n, v["color"], v["size"] / total_size * 100) for n, v in top
        ],
    }


FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif")


def svg_open(w: int, h: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}" '
        f'font-family="{FONT}">',
        f"<title>{esc(title)}</title>",
    ]


def heat_thresholds(counts: list[int]) -> tuple[int, int, int]:
    """Quartile cutoffs over *non-zero* days only.

    Scaling against the single busiest day would crush a year of ordinary days
    into the faintest shade whenever one outlier spike exists, so bucket by the
    distribution of active days instead -- the same idea GitHub's own graph uses.
    """
    active = sorted(c for c in counts if c > 0)
    if not active:
        return (1, 2, 3)

    def q(p: float) -> int:
        return active[min(len(active) - 1, int(len(active) * p))]

    return q(0.25), q(0.5), q(0.75)


def heat_index(count: int, cuts: tuple[int, int, int]) -> int:
    if count <= 0:
        return 0
    q1, q2, q3 = cuts
    if count <= q1:
        return 1
    if count <= q2:
        return 2
    if count <= q3:
        return 3
    return 4


def hunt(cols: int, alive: set[tuple[int, int]]) -> tuple[list, dict]:
    """Walk a snake that hunts contribution cells, then keeps roaming.

    The head steps one cell at a time toward the nearest remaining cell, but
    takes a random turn `DETOUR_CHANCE` of the time, so the route reads as a
    snake with a purpose rather than either a rigid sweep or a drunk walk.
    Reversing straight back on itself is disallowed, which is what stops the
    body from folding through its own neck.

    Returns the head positions per frame and the frame each cell was eaten.
    Seeded, so the animation only changes when the contribution data does.
    """
    rng = random.Random(HUNT_SEED)
    remaining = set(alive)
    # Start on the emptiest edge so the first frames are not instantly eating.
    head = (0, 3)
    path = [head]
    eaten_at: dict[tuple[int, int], int] = {}
    prev = None

    def options(pos):
        x, y = pos
        cand = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return [(a, b) for a, b in cand if 0 <= a < cols and 0 <= b < 7
                and (a, b) != prev]

    # Frame budget: enough to clear the board without spinning forever if the
    # walk somehow stalls.
    while remaining and len(path) < cols * 7 * 6:
        moves = options(head) or [head]
        if rng.random() < DETOUR_CHANCE:
            nxt = rng.choice(moves)
        else:
            tx, ty = min(remaining,
                         key=lambda c: abs(c[0] - head[0]) + abs(c[1] - head[1]))
            nxt = min(moves, key=lambda m: abs(m[0] - tx) + abs(m[1] - ty))
        prev, head = head, nxt
        path.append(head)
        if head in remaining:
            remaining.discard(head)
            eaten_at[head] = len(path) - 1

    # Roam for a second phase of equal length while the board spits cells back.
    phase = max(eaten_at.values()) if eaten_at else 1
    while len(path) < phase * 2:
        moves = options(head) or [head]
        # Mild forward bias keeps the roam from looking like jitter.
        if prev and rng.random() < 0.6:
            dx, dy = head[0] - prev[0], head[1] - prev[1]
            ahead = (head[0] + dx, head[1] + dy)
            nxt = ahead if ahead in moves else rng.choice(moves)
        else:
            nxt = rng.choice(moves)
        prev, head = head, nxt
        path.append(head)

    return path, eaten_at


def contributions_card(d: dict, theme: str) -> str:
    t = THEMES[theme]
    cell, gap = 11, 3
    step = cell + gap
    pad = 22
    left = pad + 26          # room for weekday labels
    top = pad + 54           # room for header + month labels

    weeks = d["weeks"]
    width = left + len(weeks) * step + pad
    height = top + 7 * step + 46

    counts = [day["contributionCount"] for w in weeks for day in w["contributionDays"]]
    peak = max(counts, default=0)
    cuts = heat_thresholds(counts)

    s = svg_open(width, height, f"{d['login']} contribution history")
    s.append(
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
        f'fill="{t["card"]}" stroke="{t["border"]}"/>'
    )

    # Header: title on the left, streak facts on the right.
    s.append(
        f'<text x="{pad}" y="{pad + 14}" fill="{t["text"]}" font-size="15" '
        f'font-weight="600">Contribution history</text>'
    )
    s.append(
        f'<text x="{pad}" y="{pad + 33}" fill="{t["muted"]}" font-size="12">'
        f'{d["total"]} contributions in the last year</text>'
    )
    facts = [("Current streak", f'{d["current"]}d'),
             ("Longest streak", f'{d["longest"]}d')]
    fx = width - pad
    for label, value in reversed(facts):
        s.append(
            f'<text x="{fx}" y="{pad + 14}" fill="{t["accent"]}" font-size="15" '
            f'font-weight="600" text-anchor="end">{value}</text>'
        )
        s.append(
            f'<text x="{fx}" y="{pad + 31}" fill="{t["muted"]}" font-size="10" '
            f'text-anchor="end">{label}</text>'
        )
        fx -= 104

    # Month labels: printed once, above the first week of each new month.
    seen = set()
    for wi, w in enumerate(weeks):
        first = w["contributionDays"][0]["date"]
        year, month = int(first[:4]), int(first[5:7])
        if (year, month) in seen or int(first[8:10]) > 7:
            continue
        seen.add((year, month))
        s.append(
            f'<text x="{left + wi * step}" y="{top - 8}" fill="{t["muted"]}" '
            f'font-size="10">{MONTHS[month - 1]}</text>'
        )

    for di, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        s.append(
            f'<text x="{left - 8}" y="{top + di * step + cell - 2}" '
            f'fill="{t["muted"]}" font-size="9" text-anchor="end">{label}</text>'
        )

    alive = {(wi, day["weekday"])
             for wi, w in enumerate(weeks)
             for day in w["contributionDays"]
             if day["contributionCount"] > 0}
    path, eaten_at = hunt(len(weeks), alive)

    # Every cell respawns exactly `phase` frames after it was swallowed, which
    # makes the dead window identical for each one. That is what lets a single
    # set of CSS keyframes drive all of them, with a per-cell negative delay
    # setting the phase -- otherwise each cell would need its own @keyframes.
    phase = max(eaten_at.values())
    frames = phase * 2
    period = round(frames * SNAKE_STEP_SECONDS, 2)

    s.append(
        "<style>"
        "@keyframes eat{"
        f'0%{{fill:var(--a)}}0.4%{{fill:{t["heat"][0]}}}'
        f'50%{{fill:{t["heat"][0]}}}50.4%{{fill:var(--a)}}100%{{fill:var(--a)}}'
        "}"
        f".e{{animation:eat {period}s linear infinite}}"
        "@media(prefers-reduced-motion:reduce){.e{animation:none}.sn{display:none}}"
        "</style>"
    )

    for wi, w in enumerate(weeks):
        for day in w["contributionDays"]:
            x = left + wi * step
            y = top + day["weekday"] * step
            n = day["contributionCount"]
            fill = t["heat"][heat_index(n, cuts)]
            plural = "" if n == 1 else "s"
            extra = ""
            if n > 0:
                lag = period - eaten_at[(wi, day["weekday"])] * SNAKE_STEP_SECONDS
                extra = (f' class="e" style="--a:{fill};'
                         f'animation-delay:-{lag:.2f}s"')
            s.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                f'fill="{fill}"{extra}><title>{n} contribution{plural} on '
                f'{day["date"]}</title></rect>'
            )

    # Length over time: one segment per GROW_PER_CELLS swallowed, released again
    # as those cells respawn, so the snake is back to its starting size exactly
    # when the board is full again and the loop can repeat seamlessly.
    eat_frames = sorted(eaten_at.values())
    lengths = []
    for f in range(frames):
        swallowed = bisect.bisect_right(eat_frames, f)
        respawned = bisect.bisect_right(eat_frames, f - phase)
        lengths.append(SNAKE_LENGTH
                       + swallowed // GROW_PER_CELLS
                       - respawned // GROW_PER_CELLS)
    longest_snake = max(lengths)

    # Segments live in a scaled group so each frame's coordinate is a small grid
    # index ("31,4") rather than a pixel pair ("456,78"). Across ~700 frames and
    # a 20-odd segment body that roughly halves the file.
    s.append(f'<g transform="translate({left} {top}) scale({step})">')
    unit = f"{cell / step:.4f}"
    radius = f"{3 / step:.4f}"

    for k in range(longest_snake):
        coords, shown = [], []
        for f in range(frames):
            wi, r = path[max(0, f - k)]
            coords.append(f"{wi},{r}")
            shown.append("1" if k < lengths[f] else "0")
        if k == 0:
            fill, base = t["snake_head"], 1.0
        else:
            fill = t["snake_body"]
            # Taper along the body, with a floor so a long tail stays visible.
            base = max(0.35, 1 - k / (longest_snake + 2))
        # Only segments that come and go need the extra opacity track.
        fade = ""
        if "0" in shown:
            fade = (f'<animate attributeName="opacity" calcMode="discrete" '
                    f'dur="{period}s" repeatCount="indefinite" '
                    f'values="{";".join(str(round(base * int(v), 2)) for v in shown)}"/>')
        s.append(
            f'<rect class="sn" width="{unit}" height="{unit}" rx="{radius}" '
            f'fill="{fill}" opacity="{base if k < SNAKE_LENGTH else 0}" '
            # Static fallback position: without this, a renderer that ignores
            # SMIL stacks every segment at the card's top-left corner.
            f'transform="translate({coords[0].replace(",", " ")})">'
            f'<animateTransform attributeName="transform" type="translate" '
            f'calcMode="discrete" dur="{period}s" repeatCount="indefinite" '
            f'values="{";".join(coords)}"/>{fade}'
            f"</rect>"
        )

    s.append("</g>")

    ly = top + 7 * step + 22
    s.append(
        f'<text x="{pad}" y="{ly + 9}" fill="{t["muted"]}" font-size="10">Less</text>'
    )
    lx = pad + 32
    for shade in t["heat"]:
        s.append(
            f'<rect x="{lx}" y="{ly}" width="{cell}" height="{cell}" rx="2" '
            f'fill="{shade}"/>'
        )
        lx += step
    s.append(
        f'<text x="{lx + 2}" y="{ly + 9}" fill="{t["muted"]}" font-size="10">More</text>'
    )
    s.append(
        f'<text x="{width - pad}" y="{ly + 9}" fill="{t["muted"]}" font-size="10" '
        f'text-anchor="end">peak {peak} in a day</text>'
    )

    s.append("</svg>")
    return "\n".join(s)


def stats_card(d: dict, theme: str) -> str:
    t = THEMES[theme]
    pad = 22
    width, height = 880, 232
    mid = 470

    s = svg_open(width, height, f"{d['login']} GitHub statistics")
    s.append(
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
        f'fill="{t["card"]}" stroke="{t["border"]}"/>'
    )
    s.append(
        f'<text x="{pad}" y="{pad + 14}" fill="{t["text"]}" font-size="15" '
        f'font-weight="600">{esc(d["name"])} — GitHub stats</text>'
    )
    s.append(
        f'<text x="{pad}" y="{pad + 33}" fill="{t["muted"]}" font-size="12">'
        f'@{esc(d["login"])}</text>'
    )

    tiles = [
        ("Commits (last yr)", human(d["commits"])),
        ("Pull requests", human(d["prs"])),
        ("Contributions", human(d["total"])),
        ("Public repos", human(d["repos"])),
        ("Stars earned", human(d["stars"])),
        ("Longest streak", f'{d["longest"]}d'),
    ]
    col_w = 146
    for i, (label, value) in enumerate(tiles):
        x = pad + (i % 3) * col_w
        y = pad + 66 + (i // 3) * 62
        s.append(
            f'<text x="{x}" y="{y + 20}" fill="{t["accent"]}" font-size="22" '
            f'font-weight="700">{value}</text>'
        )
        s.append(
            f'<text x="{x}" y="{y + 38}" fill="{t["muted"]}" font-size="10.5">'
            f'{label}</text>'
        )

    s.append(
        f'<line x1="{mid - 24}" y1="{pad + 4}" x2="{mid - 24}" y2="{height - pad - 4}" '
        f'stroke="{t["border"]}"/>'
    )
    s.append(
        f'<text x="{mid}" y="{pad + 14}" fill="{t["text"]}" font-size="13" '
        f'font-weight="600">Most used languages</text>'
    )

    bar_w = width - mid - pad
    y = pad + 42
    for name, color, pct in d["langs"]:
        s.append(
            f'<text x="{mid}" y="{y}" fill="{t["text"]}" font-size="11">'
            f'{esc(name)}</text>'
        )
        s.append(
            f'<text x="{mid + bar_w}" y="{y}" fill="{t["muted"]}" font-size="10" '
            f'text-anchor="end">{pct:.1f}%</text>'
        )
        s.append(
            f'<rect x="{mid}" y="{y + 5}" width="{bar_w}" height="7" rx="3.5" '
            f'fill="{t["track"]}"/>'
        )
        filled = max(3.5, bar_w * pct / 100)
        s.append(
            f'<rect x="{mid}" y="{y + 5}" width="{filled:.1f}" height="7" rx="3.5" '
            f'fill="{color}"/>'
        )
        y += 29

    s.append("</svg>")
    return "\n".join(s)


def main() -> None:
    data = collect(fetch(USER))
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for theme in ("light", "dark"):
        suffix = "" if theme == "light" else "-dark"
        for stem, render in (("stats", stats_card),
                             ("contributions", contributions_card)):
            path = OUT / f"{stem}{suffix}.svg"
            path.write_text(render(data, theme) + "\n", encoding="utf-8")
            written.append(path.name)
    print(f"{data['total']} contributions | wrote: {', '.join(written)}")


if __name__ == "__main__":
    main()
