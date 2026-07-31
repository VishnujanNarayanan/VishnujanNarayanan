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
import heapq
from collections import deque
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
SNAKE_STEP_SECONDS = 0.04    # one grid step per frame
SNAKE_LENGTH = 4             # starting length, and the length it returns to
GROW_PER_CELLS = 12          # cells swallowed per extra body segment
DETOUR_CHANCE = 0.12         # how often the head wanders off the direct line
SOW_DETOUR_CHANCE = 0.0      # the respawn tour runs straight, no wandering
FAR_TARGET_CHANCE = 0.1      # share of targets picked from the far half
CROSS_PENALTY = 12           # cost of routing back over an already sown dot
HEAD_SCALE = 1.14            # head, relative to a contribution cell
TAIL_SHORT = 0.65            # tail size when the snake is back to its shortest
TAIL_LONG = 0.45             # tail size at full stretch
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


def hunt(cols: int, alive: set[tuple[int, int]]) -> dict:
    """Simulate a snake that clears the board, then sows it back.

    Phase one eats every contribution cell; phase two tours them again and each
    reappears as the tail clears it. The head never steps onto its own body --
    only the tail cell, which is vacated on the same frame -- and a flood-fill
    check keeps it out of pockets it could not escape.

    Targets are held until reached rather than recomputed every frame, and
    `FAR_TARGET_CHANCE` of them are picked at random from anywhere on the board
    instead of nearest-first. Always chasing the nearest cell makes the snake
    exhaust one region before grudgingly moving on; committing to an occasional
    distant target is what sends it across the whole board.

    The route closes: it finishes adjacent to where it started, so the renderer
    can index the path modulo its length and the loop carries no seam.

    Seeded, so the animation only changes when the contribution data does.
    """
    rng = random.Random(HUNT_SEED)
    remaining = set(alive)
    head = (0, 3)
    path = [head]
    eaten_at: dict[tuple[int, int], int] = {}
    body = deque([head])          # head first, tail last
    occupied = {head}
    banned: set[tuple[int, int]] = set()
    lengths = [SNAKE_LENGTH]      # the body length actually enforced per frame

    def neighbours(pos):
        x, y = pos
        return [(a, b) for a, b in
                ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                if 0 <= a < cols and 0 <= b < 7]

    def room(start, blocked, cap):
        """Free cells reachable from `start`, counted up to `cap`.

        Greedy hunting will happily walk into a pocket it cannot get out of,
        which is the only way this snake ever collides. Rejecting moves whose
        reachable space is smaller than the body avoids the trap in the first
        place, rather than handling the crash afterwards.
        """
        seen = {start}
        stack = [start]
        while stack and len(seen) < cap:
            for n in neighbours(stack.pop()):
                if n not in seen and n not in blocked:
                    seen.add(n)
                    stack.append(n)
        return len(seen)

    def step(target, detour=DETOUR_CHANCE):
        """Pick the next cell, preferring progress toward `target`."""
        cand = neighbours(head)
        # The tail vacates as we advance, so treat it as free; everything else
        # in the body is a collision.
        tail = body[-1]
        pick_from = [c for c in cand
                     if (c not in occupied or c == tail) and c not in banned]
        if not pick_from:
            # Boxed in anyway. Step onto the oldest body cell available, which
            # clears soonest, so any overlap is as brief as possible.
            order = {c: i for i, c in enumerate(body)}
            return max(cand, key=lambda c: order.get(c, -1)) if cand else head

        need = len(body) + 1
        after = (occupied - {tail}) | banned
        roomy = [c for c in pick_from if room(c, after - {c}, need) >= need]
        pick = roomy or pick_from

        if target is None or rng.random() < detour:
            return rng.choice(pick)
        return min(pick, key=lambda m: abs(m[0] - target[0]) + abs(m[1] - target[1]))

    def plan(goals, sown):
        """Cheapest route from the head to the nearest goal.

        Crossing a dot already sown is allowed but expensive, so the tour walks
        around its own work when there is a way round and only cuts across when
        that is the only option. Greedy single-stepping cannot do this: told to
        avoid sown dots outright it wanders among clean cells that lead nowhere
        and the tour never finishes, which is exactly what stalled it.
        """
        blocked = set(list(body)[:-1])
        dist = {head: 0}
        prev: dict = {}
        queue = [(0, head)]
        goal = None
        while queue:
            cost, cur = heapq.heappop(queue)
            if cost > dist.get(cur, 1 << 30):
                continue
            if cur in goals and cur != head:
                goal = cur
                break
            for n in neighbours(cur):
                if n in blocked:
                    continue
                nxt_cost = cost + 1 + (CROSS_PENALTY if n in sown else 0)
                if nxt_cost < dist.get(n, 1 << 30):
                    dist[n] = nxt_cost
                    prev[n] = cur
                    heapq.heappush(queue, (nxt_cost, n))
        if goal is None:
            return []
        route = []
        node = goal
        while node != head:
            route.append(node)
            node = prev[node]
        route.reverse()
        return route

    def advance(nxt, length):
        nonlocal head
        head = nxt
        path.append(head)
        body.appendleft(head)
        while len(body) > length:
            occupied.discard(body.pop())
        occupied.add(head)
        lengths.append(len(body))

    def aim(pool, current, far=FAR_TARGET_CHANCE):
        """Hold a target until it is gone; sometimes commit to a distant one."""
        if current in pool:
            return current
        if not pool:
            return None
        if rng.random() < far:
            # Bias toward the far half of the board so the snake actually
            # crosses it rather than nibbling whatever is next door.
            ranked = sorted(pool, key=lambda c: -(abs(c[0] - head[0])
                                                  + abs(c[1] - head[1])))
            return rng.choice(ranked[:max(1, len(ranked) // 2)])
        return min(pool, key=lambda c: abs(c[0] - head[0]) + abs(c[1] - head[1]))

    length = SNAKE_LENGTH
    target = None
    while remaining and len(path) < cols * 7 * 6:
        target = aim(remaining, target)
        advance(step(target), length)
        if head in remaining:
            remaining.discard(head)
            eaten_at[head] = len(path) - 1
            length = SNAKE_LENGTH + len(eaten_at) // GROW_PER_CELLS

    # Phase two: a second tour over the same cells. A cell reappears on the
    # frame the *tail* clears it, so the snake sows the board back in behind
    # itself -- which is why the respawn frame is the head's arrival plus the
    # current body length, the point at which the body no longer covers it.
    swallowed = len(eaten_at)
    to_sow = set(eaten_at)
    respawn_at: dict[tuple[int, int], int] = {}
    due: dict[int, int] = {}
    returned = 0

    sown: set[tuple[int, int]] = set()
    route: list = []
    ceiling = len(path) + cols * 7 * 8      # guard against an unfinishable tour
    while (to_sow or len(path) <= max(respawn_at.values(), default=0)) \
            and len(path) < ceiling:
        f = len(path)
        returned += due.pop(f, 0)
        # Length tracks how much of the board is still missing, rather than
        # counting down at a fixed rate per cell sown. A fixed rate bottomed the
        # snake out a quarter of the way through the tour and left it at minimum
        # for the rest; this way it is still visibly long at halfway and only
        # reaches its starting size as the last dots go back.
        left = swallowed - returned
        length = SNAKE_LENGTH + round(swallowed // GROW_PER_CELLS * left / swallowed)
        # Follow a planned route rather than stepping greedily, replanning
        # whenever the body gets in the way of the next square.
        if to_sow and not route:
            route = plan(to_sow, sown)
        if route:
            nxt = route[0]
            if nxt in occupied and nxt != body[-1]:
                route = []
                nxt = step(None, SOW_DETOUR_CHANCE)
            else:
                route.pop(0)
        else:
            nxt = step(None, SOW_DETOUR_CHANCE)
        advance(nxt, length)
        if head in to_sow:
            to_sow.discard(head)
            sown.add(head)
            clear = f + length
            respawn_at[head] = clear
            due[clear] = due.get(clear, 0) + 1

    # Close the loop: walk home until the head sits one cell from where it
    # began, so restarting is a single legal step instead of a teleport. The
    # renderer indexes the path modulo its length, so the body wraps too.
    start = path[0]
    # Off limits on the way home: walking through the start cell would put it in
    # the body twice once the path wraps, and the seam is exactly where that
    # shows.
    # Keep clear of the sown dots on the way home as well: parking the body on
    # one would hold it dark past the frame it was due to reappear.
    banned.clear()
    banned.update(sown)
    banned.add(start)
    guard = cols * 7 * 2
    while guard > 0:
        # Stop only once the head is one step from home *and* the cells that
        # will wrap into the body at frame zero are clear of the start cell --
        # otherwise the start appears twice in the body across the seam.
        wraps = path[-(SNAKE_LENGTH - 1):] if SNAKE_LENGTH > 1 else []
        if head in neighbours(start) and start not in wraps:
            break
        advance(step(start), SNAKE_LENGTH)
        guard -= 1
    banned.discard(start)

    # The homing walk and the wrapped body can both put the snake back over a
    # cell exactly as it was due to reappear, which would pop it in underneath
    # the body. Slide those few forward to the next clear frame.
    frames = len(path)

    def covered(cell, f):
        return any(path[(f - k) % frames] == cell for k in range(lengths[f]))

    for c, due_at in respawn_at.items():
        f = due_at
        while f < frames - 1 and covered(c, f):
            f += 1
        respawn_at[c] = f

    return {"path": path, "eaten_at": eaten_at, "respawn_at": respawn_at,
            "frames": frames, "lengths": lengths}


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
    sim = hunt(len(weeks), alive)
    path, eaten_at = sim["path"], sim["eaten_at"]
    respawn_at, frames = sim["respawn_at"], sim["frames"]
    period = round(frames * SNAKE_STEP_SECONDS, 2)

    # Because cells now respawn in reverse order, the dead window differs per
    # cell, so they cannot share one set of keyframes offset by a delay. Each
    # cell gets its own rule instead -- still cheap, and it keeps the whole
    # animation in CSS so prefers-reduced-motion can switch it off.
    rules = [f".e{{animation-duration:{period}s;animation-timing-function:step-end;"
             "animation-iteration-count:infinite}"]
    dead = t["heat"][0]
    cell_class: dict[tuple[int, int], str] = {}
    for i, (pos, gone) in enumerate(sorted(eaten_at.items(), key=lambda kv: kv[1])):
        back = respawn_at[pos]
        a = gone / frames * 100
        b = min(99.9, back / frames * 100)
        cell_class[pos] = f"k{i}"
        rules.append(
            f"@keyframes k{i}{{0%{{fill:var(--a)}}{a:.2f}%{{fill:{dead}}}"
            f"{b:.2f}%{{fill:var(--a)}}}}.k{i}{{animation-name:k{i}}}"
        )
    style_at = len(s)      # placeholder; filled once the snake rules exist
    s.append("")
    body_rules: list[str] = []

    for wi, w in enumerate(weeks):
        for day in w["contributionDays"]:
            x = left + wi * step
            y = top + day["weekday"] * step
            n = day["contributionCount"]
            fill = t["heat"][heat_index(n, cuts)]
            plural = "" if n == 1 else "s"
            extra = ""
            if n > 0:
                extra = (f' class="e {cell_class[(wi, day["weekday"])]}"'
                         f' style="--a:{fill}"')
            s.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                f'fill="{fill}"{extra}><title>{n} contribution{plural} on '
                f'{day["date"]}</title></rect>'
            )

    # Length over time: one segment per GROW_PER_CELLS swallowed, released again
    # as those cells respawn, so the snake is back to its starting size exactly
    # when the board is full again and the loop can repeat seamlessly.
    # Taken straight from the simulation: the drawn body must be the same body
    # that was collision-checked, or the snake appears to cross itself.
    lengths = sim["lengths"][:frames]
    longest_snake = max(lengths)

    # Segments live in a scaled group so each frame's coordinate is a small grid
    # index ("31,4") rather than a pixel pair ("456,78"). Across ~700 frames and
    # a 20-odd segment body that roughly halves the file.
    s.append(f'<g transform="translate({left} {top}) scale({step})">')
    unit = cell / step

    def taper(k, live):
        """Size of segment `k` on a body currently `live` segments long.

        The tail thins out as the snake grows: TAIL_SHORT when it is back to
        its starting length, TAIL_LONG at full stretch. Segment size therefore
        depends on the live length, not just position, so it has to be animated
        rather than baked into the rect.
        """
        if live <= 1:
            return HEAD_SCALE
        span = max(1, longest_snake - SNAKE_LENGTH)
        grown = min(1.0, max(0.0, (live - SNAKE_LENGTH) / span))
        tail = TAIL_SHORT + (TAIL_LONG - TAIL_SHORT) * grown
        return HEAD_SCALE + (tail - HEAD_SCALE) * (k / (live - 1))

    # Length only changes a few dozen times a loop, so keying size and opacity
    # off those moments keeps each segment's keyframes small.
    shifts = [0] + [f for f in range(1, frames) if lengths[f] != lengths[f - 1]]

    for k in range(longest_snake):
        if k == 0:
            fill, base = t["snake_head"], 1.0
        else:
            fill = t["snake_body"]
            # Fade along the body too, with a floor so a long tail stays visible.
            base = max(0.35, 1 - k / (longest_snake + 2))

        # Every segment replays the head's track, lagging by its position in the
        # body, so they all share the one `slither` keyframe set.
        #
        # A negative delay starts an animation part-way in, so -k*step would put
        # segment k that many frames *ahead* of the head and the snake would run
        # tail first. To lag by k frames on a loop, wind back a whole period
        # instead: -(period - k*step).
        lag = -((period - k * SNAKE_STEP_SECONDS) % period)
        anims = [f"slither {period}s step-end {lag:.3f}s infinite"]

        marks = []
        for f in shifts:
            live = lengths[f]
            if k < live:
                marks.append((f / frames * 100, taper(k, live), base))
            else:
                marks.append((f / frames * 100, TAIL_LONG, 0.0))
        # Collapse runs where nothing changed.
        trimmed = [marks[0]]
        for m in marks[1:]:
            if (m[1], m[2]) != (trimmed[-1][1], trimmed[-1][2]):
                trimmed.append(m)
        body_rules.append(
            f"@keyframes b{k}{{"
            + "".join(f"{pct:.4f}%{{transform:scale({sc:.4f});opacity:{op}}}"
                      for pct, sc, op in trimmed)
            + "}"
        )
        anims.append(f"b{k} {period}s step-end 0s infinite")
        body_rules.append(f".s{k}>rect{{animation:{anims[1]}}}")
        body_rules.append(f".s{k}{{animation:{anims[0]}}}")

        # Two nested elements because the two transforms run on different
        # clocks: the group carries the shared route with a per-segment delay,
        # the rect carries its own size track with none.
        wi, r = path[(0 - k) % frames]
        start = taper(k, lengths[0]) if k < lengths[0] else TAIL_LONG
        s.append(
            f'<g class="sn s{k}" transform="translate({wi + unit / 2:.4f} '
            f'{r + unit / 2:.4f})">'
            f'<rect x="{-unit / 2:.4f}" y="{-unit / 2:.4f}" '
            f'width="{unit:.4f}" height="{unit:.4f}" rx="{3 / step:.4f}" '
            f'fill="{fill}" opacity="{base if k < lengths[0] else 0}" '
            f'transform="scale({start:.4f})"/>'
            f"</g>"
        )

    s.append("</g>")

    # One keyframe set for the head's whole route. Segment k is the same track
    # delayed by k frames, which is why 15 segments cost one set of keyframes
    # rather than fifteen.
    half = unit / 2
    track = "".join(
        f"{f / frames * 100:.4f}%{{transform:"
        f"translate({path[f][0] + half:.3f}px,{path[f][1] + half:.3f}px)}}"
        for f in range(frames)
    )
    rules.append(".sn>rect{transform-box:fill-box;transform-origin:center}")
    rules.append(f"@keyframes slither{{{track}}}")
    rules.extend(body_rules)
    rules.append(
        "@media(prefers-reduced-motion:reduce){.e,.sn,.sn>rect{animation:none}}"
    )
    s[style_at] = "<style>" + "".join(rules) + "</style>"

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
