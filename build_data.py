"""Build usage-trend and start/sit data for the website from nflverse files.
Usage: build_data.py SNAPS.csv STATS.csv GAMES.csv OUT.json
"""
import json, re, sys
import pandas as pd

snap_path, stats_path, games_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
s = pd.read_csv(snap_path)
p = pd.read_csv(stats_path, low_memory=False)

SKILL = ["QB", "RB", "WR", "TE"]

def norm(n):
    n = str(n).lower()
    n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", n)
    return re.sub(r"[^a-z]", "", n)

s = s[s.position.isin(SKILL)].copy()
s["key"] = s.player.map(norm)
p = p[p.position.isin(SKILL)].copy()
p["key"] = p.player_display_name.map(norm)

# team totals for carry share (sum of all player carries that week)
allp = pd.read_csv(stats_path, low_memory=False)
team_car = allp.groupby(["team", "week"]).carries.sum().rename("team_carries")
p = p.join(team_car, on=["team", "week"])
p["carry_share"] = (p.carries / p.team_carries).where(p.team_carries > 0)

cols = ["key", "team", "week", "player_display_name", "position", "carries", "targets",
        "receptions", "rushing_yards", "receiving_yards", "rushing_tds", "receiving_tds",
        "passing_yards", "passing_tds", "target_share", "carry_share", "fantasy_points_ppr", "opponent_team", "headshot_url"]
# fallback for nickname mismatches (Kenneth/Kenny, Zonovan/Bam): match on last name + team + week + position
def last(n):
    parts = [x for x in re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", str(n).lower()).split() if x]
    return re.sub(r"[^a-z]", "", parts[-1]) if parts else ""
s["lkey"] = s.player.map(last)
p["lkey"] = p.player_display_name.map(last)
exact = set(zip(p.key, p.team, p.week))
lookup = p.groupby(["lkey", "team", "week", "position"]).key.agg(list)
def fix(r):
    if (r.key, r.team, r.week) in exact:
        return r.key
    c = lookup.get((r.lkey, r.team, r.week, r.position))
    return c[0] if c is not None and len(c) == 1 else r.key
s["key"] = s.apply(fix, axis=1)
m = s.merge(p[cols], on=["key", "team", "week"], how="left", suffixes=("", "_st"))
print("unmatched skill rows with 20%+ snaps:", int(((m.player_display_name.isna()) & (m.offense_pct >= 0.2)).sum()))
m["name"] = m.player
m["pos"] = m.position

num = ["carries", "targets", "receptions", "rushing_yards", "receiving_yards", "rushing_tds",
       "receiving_tds", "passing_yards", "passing_tds", "fantasy_points_ppr"]
m[num] = m[num].fillna(0)
m["target_share"] = m.target_share.fillna(0)
m["carry_share"] = m.carry_share.fillna(0)
m["opp"] = m.opponent

max_week = int(m.week.max())
players = []
for (pid, name), g in m.groupby(["pfr_player_id", "name"]):
    g = g.sort_values("week")
    pos = g.pos.iloc[-1]
    team = g.team.iloc[-1]
    weeks = []
    for _, r in g.iterrows():
        weeks.append({
            "w": int(r.week), "opp": r.opp, "snap": round(float(r.offense_pct) * 100, 1),
            "tgt": int(r.targets), "tgtSh": round(float(r.target_share) * 100, 1),
            "car": int(r.carries), "carSh": round(float(r.carry_share) * 100, 1),
            "rec": int(r.receptions), "yds": int(r.rushing_yards + r.receiving_yards),
            "td": int(r.rushing_tds + r.receiving_tds), "pyds": int(r.passing_yards),
            "ptd": int(r.passing_tds), "pts": round(float(r.fantasy_points_ppr), 1),
            "ptsH": round(float(r.fantasy_points_ppr) - 0.5 * float(r.receptions), 1),
        })
    # only keep fantasy-relevant players: played recently with real role
    recent = [w for w in weeks if w["w"] > max_week - 3]
    if not recent:
        continue
    if max(w["snap"] for w in weeks) < 25:
        continue
    def avg(ws, k):
        return round(sum(x[k] for x in ws) / len(ws), 1) if ws else 0
    usage_key = "tgtSh" if pos in ("WR", "TE") else ("carSh" if pos == "RB" else "snap")
    # Two trend windows: last game played, and last 3 games played (bye weeks skipped),
    # each compared with all of his games before that window.
    tr = {}
    for wn in (1, 3):
        recent_w, prior = weeks[-wn:], weeks[:-wn]
        has = bool(prior)
        d = {"snapL": avg(recent_w, "snap"), "snapPrior": avg(prior, "snap"),
             "oppL": round(avg(recent_w, "tgt") + avg(recent_w, "car"), 1),
             "oppPrior": round(avg(prior, "tgt") + avg(prior, "car"), 1),
             "useL": avg(recent_w, usage_key), "usePrior": avg(prior, usage_key),
             "ptsL": avg(recent_w, "pts"), "ptsLH": avg(recent_w, "ptsH"), "hasPrior": has}
        d["snapDelta"] = round(d["snapL"] - d["snapPrior"], 1) if has else None
        d["oppDelta"] = round(d["oppL"] - d["oppPrior"], 1) if has else None
        d["useDelta"] = round(d["useL"] - d["usePrior"], 1) if has else None
        tr[str(wn)] = d
    players.append({
        "id": pid, "name": name, "pos": pos, "team": team, "weeks": weeks,
        "games": len(weeks), "tr": tr,
        "ppg": avg(weeks, "pts"), "ppgH": avg(weeks, "ptsH"),
        # top-level trend fields mirror the "last game" window (the site's default)
        "oppDelta": tr["1"]["oppDelta"], "snapDelta": tr["1"]["snapDelta"], "hasPrior": tr["1"]["hasPrior"],
    })

# ---------------- Start/sit for the upcoming week ----------------
season = int(s.season.iloc[0]) if "season" in s else 2026
g = pd.read_csv(games_path)
g = g[(g.season == season) & (g.game_type == "REG")]
# Upcoming week = first week whose opening game is still ahead (4-day cushion keeps
# a week "upcoming" through its own Sunday, and moves on once its Monday game is done).
today = pd.Timestamp.now(tz="America/New_York").tz_localize(None).normalize()
first_day = g.groupby("week").gameday.min().map(pd.Timestamp)
ahead = first_day[first_day > today - pd.Timedelta(days=4)]
upcoming = None
if len(ahead):
    upcoming = int(ahead.index.min())
    wk = g[g.week == upcoming]
    # Vegas implied team totals (spread_line > 0 means home team favored)
    lg_imp = 22.5
    opp_of, home_of, imp_of, day_of = {}, {}, {}, {}
    for _, r in wk.iterrows():
        tot, spr = r.get("total_line"), r.get("spread_line")
        has = pd.notna(tot) and pd.notna(spr)
        hi = (tot / 2 + spr / 2) if has else None
        ai = (tot / 2 - spr / 2) if has else None
        opp_of[r.home_team], opp_of[r.away_team] = r.away_team, r.home_team
        home_of[r.home_team], home_of[r.away_team] = True, False
        imp_of[r.home_team], imp_of[r.away_team] = hi, ai
        day_of[r.home_team] = day_of[r.away_team] = str(r.gameday)

    # Scoring systems: full PPR (1 pt per catch) and half PPR (0.5 per catch)
    allp = allp.copy()
    allp["pts_full"] = allp.fantasy_points_ppr
    allp["pts_half"] = allp.fantasy_points_ppr - 0.5 * allp.receptions.fillna(0)
    SC = {"full": ("pts_full", "pts", "ppg", 1.0), "half": ("pts_half", "ptsH", "ppgH", 0.5)}
    games_by_def = allp.groupby("opponent_team").week.nunique()
    sk = allp[allp.position.isin(SKILL)].copy()
    for c in ["carries", "targets", "receptions", "rushing_yards", "rushing_tds", "receiving_yards", "receiving_tds"]:
        sk[c] = sk[c].fillna(0)
    lg_avg_out = {}
    K = 2  # "phantom" average games added to every player: 1-2 game samples get pulled toward normal
    for sc, (col, wkey, ppgkey, rec_pts) in SC.items():
        # Defense: fantasy points allowed per game to each position
        allowed = sk.groupby(["opponent_team", "position"])[col].sum().unstack(fill_value=0).div(games_by_def, axis=0)
        lg_avg = allowed.mean()
        ranks = allowed.rank(ascending=False, method="min")  # 1 = gives up the MOST (easiest matchup)
        lg_avg_out[sc] = {pos: round(float(lg_avg[pos]), 1) for pos in SKILL if pos in lg_avg}
        # Value of one carry / one target at each position (league-wide, this season)
        rush_pts = 0.1 * sk.rushing_yards + 6 * sk.rushing_tds
        rec_pts_all = rec_pts * sk.receptions + 0.1 * sk.receiving_yards + 6 * sk.receiving_tds
        vcar = (rush_pts.groupby(sk.position).sum() / sk.groupby("position").carries.sum()).to_dict()
        vtgt = (rec_pts_all.groupby(sk.position).sum() / sk.groupby("position").targets.sum()).to_dict()
        # Position baseline: median points per game of established players (3+ games)
        prior = {pos: float(pd.Series([p[ppgkey] for p in players if p["pos"] == pos and p["games"] >= 3]).median())
                 for pos in SKILL}
        for pl in players:
            t, pos = pl["team"], pl["pos"]
            if t not in opp_of:
                continue
            ws = pl["weeks"]
            recent = ws[-3:]
            n = len(ws)
            l3 = sum(w[wkey] for w in recent) / len(recent)
            form = 0.3 * l3 + 0.7 * pl[ppgkey]   # season-long role matters most; last 3 adds recent form
            if pos == "QB":
                xform = form
            else:
                xp = lambda w: w["car"] * vcar[pos] + w["tgt"] * vtgt[pos]
                xform = 0.3 * sum(xp(w) for w in recent) / len(recent) + 0.7 * sum(xp(w) for w in ws) / n
            blend = 0.6 * form + 0.4 * xform           # mostly actual points, plus what his usage is usually worth
            k = K if n < 4 else 0                      # only 1-3 game samples get pulled toward the position baseline
            base = (n * blend + k * prior[pos]) / (n + k)
            opp = opp_of[t]
            pa = float(allowed.loc[opp, pos]) if opp in allowed.index else None
            # matchup and Vegas only nudge the number (25% strength) so studs stay studs
            dfac = 1 + 0.25 * (pa / lg_avg[pos] - 1) if pa is not None and lg_avg[pos] else 1
            imp = imp_of.get(t)
            vfac = 1 + 0.25 * (imp / lg_imp - 1) if imp else 1
            pl.setdefault("ss", {"opp": opp, "home": home_of[t], "day": day_of[t],
                                 "imp": round(imp, 1) if imp else None})
            pl["ss"][sc] = {"proj": round(base * dfac * vfac, 1), "l3": round(l3, 1), "xform": round(xform, 1),
                            "base": round(base, 1), "defRank": int(ranks.loc[opp, pos]) if pa is not None else None,
                            "defPA": round(pa, 1) if pa is not None else None}
        # "Must start" tier: the top season scorers at each position always rank first
        TIER = {"QB": 4, "RB": 5, "WR": 6, "TE": 3}
        for pos in SKILL:
            playing = [p for p in players if p["pos"] == pos and sc in p.get("ss", {})]
            studs = {p["id"] for p in sorted([p for p in playing if p["games"] >= 3], key=lambda p: -p[ppgkey])[:TIER[pos]]}
            for p in playing:
                p["ss"][sc]["must"] = p["id"] in studs
            ranked = sorted(playing, key=lambda p: (not p["ss"][sc]["must"], -p["ss"][sc]["proj"]))
            for i, p in enumerate(ranked, 1):
                p["ss"][sc]["rank"] = i
    for pl in players:
        if pl["team"] not in opp_of:
            pl["ss"] = {"bye": True}
else:
    defense, lg_avg_out = {}, {}

out = {"season": season, "throughWeek": max_week, "upcomingWeek": upcoming,
       "leagueAvgAllowed": lg_avg_out, "players": players}
with open(out_path, "w") as f:
    json.dump(out, f, separators=(",", ":"))
print(len(players), "players; through week", max_week)
