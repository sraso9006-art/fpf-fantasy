"""Build team scheme profiles from free nflverse data.
Usage: build_schemes.py PBP.csv.gz FTN.csv STATS.csv GAMES.csv OUT.json
"""
import json, sys
import pandas as pd

pbp_path, ftn_path, stats_path, games_path, out_path = sys.argv[1:6]
cols = ["game_id", "play_id", "week", "posteam", "play_type", "pass", "rush", "xpass", "epa", "down", "wp",
        "half_seconds_remaining", "air_yards", "receiver_player_id", "rusher_player_id", "run_gap",
        "run_location", "qb_scramble", "two_point_attempt", "yardline_100", "drive", "shotgun", "season_type"]
p = pd.read_csv(pbp_path, low_memory=False, usecols=lambda c: c in cols)
p = p[(p.season_type == "REG") & p.posteam.notna()]
plays = p[p.play_type.isin(["pass", "run"]) & (p.two_point_attempt.fillna(0) == 0)].copy()

st = pd.read_csv(stats_path, low_memory=False)
pos_of = st.drop_duplicates("player_id").set_index("player_id").position.to_dict()
plays["rec_pos"] = plays.receiver_player_id.map(pos_of)
plays["rush_pos"] = plays.rusher_player_id.map(pos_of)

games = plays.groupby("posteam").game_id.nunique()
T = pd.DataFrame(index=games.index)
T["games"] = games
T["pace"] = plays.groupby("posteam").size() / games

# Neutral situations: downs 1-3, win prob 20-80%, outside the last 2 minutes of each half
neu = plays[plays.down.isin([1, 2, 3]) & plays.wp.between(.2, .8) & (plays.half_seconds_remaining > 120) & plays.xpass.notna()]
T["proe"] = (neu.groupby("posteam")["pass"].mean() - neu.groupby("posteam").xpass.mean()) * 100
T["passRate"] = neu.groupby("posteam")["pass"].mean() * 100
T["epa"] = plays.groupby("posteam").epa.mean()
rz = plays[plays.yardline_100 <= 20].groupby("posteam").apply(lambda d: d[["game_id", "drive"]].drop_duplicates().shape[0], include_groups=False)
T["rzTrips"] = rz / games

att = plays[(plays.play_type == "pass") & plays.air_yards.notna()]
T["adot"] = att.groupby("posteam").air_yards.mean()
T["deep"] = att.assign(d=att.air_yards >= 20).groupby("posteam").d.mean() * 100
tg = plays[plays.receiver_player_id.notna()]
for pos in ["RB", "WR", "TE"]:
    T[f"tgt{pos}"] = tg.assign(x=tg.rec_pos == pos).groupby("posteam").x.mean() * 100

rb_runs = plays[(plays.play_type == "run") & (plays.rush_pos == "RB") & (plays.qb_scramble.fillna(0) == 0)]
T["rb1Share"] = rb_runs.groupby("posteam").apply(lambda d: d.rusher_player_id.value_counts(normalize=True).iloc[0], include_groups=False) * 100
dirn = rb_runs[rb_runs.run_location.notna()]
T["outside"] = dirn.assign(o=dirn.run_gap == "end").groupby("posteam").o.mean() * 100
T["shotgun"] = plays.groupby("posteam").shotgun.mean() * 100

# FTN charting: play-action share of dropbacks, motion share of plays
f = pd.read_csv(ftn_path)
fx = plays.merge(f[["nflverse_game_id", "nflverse_play_id", "is_play_action", "is_motion", "is_screen_pass", "is_rpo"]],
                 left_on=["game_id", "play_id"], right_on=["nflverse_game_id", "nflverse_play_id"], how="inner")
drop = fx[fx["pass"] == 1]
T["playAction"] = drop.groupby("posteam").is_play_action.mean() * 100
T["motion"] = fx.groupby("posteam").is_motion.mean() * 100
T["screen"] = drop.groupby("posteam").is_screen_pass.mean() * 100
ftn_week = int(f.groupby("week").size().pipe(lambda s: s[s > 1000]).index.max())

# Fantasy points produced per game, by position (full and half PPR)
st = st[(st.season_type == "REG") & st.position.isin(["QB", "RB", "WR", "TE"])].copy()
st["half"] = st.fantasy_points_ppr - 0.5 * st.receptions.fillna(0)
tg_games = st.groupby("team").week.nunique()
for sc, col in (("full", "fantasy_points_ppr"), ("half", "half")):
    fp = st.groupby(["team", "position"])[col].sum().unstack(fill_value=0).div(tg_games, axis=0)
    for pos in ["QB", "RB", "WR", "TE"]:
        T[f"fp{pos}_{sc}"] = fp[pos]
    T[f"fpAll_{sc}"] = fp[["QB", "RB", "WR", "TE"]].sum(axis=1)

# Points scored per game from the schedule
g = pd.read_csv(games_path)
g = g[(g.season == int(st.season.iloc[0])) & (g.game_type == "REG") & g.home_score.notna()]
pts = pd.concat([g[["home_team", "home_score"]].set_axis(["team", "pts"], axis=1),
                 g[["away_team", "away_score"]].set_axis(["team", "pts"], axis=1)])
T["ppg"] = pts.groupby("team").pts.mean()

# Key players: top 4 fantasy scorers, with carry share and target share
team_car = st.groupby("team").carries.sum()
team_tgt = st.groupby("team").targets.sum()
pl = st.groupby(["team", "player_display_name", "position"]).agg(
    pts=("fantasy_points_ppr", "sum"), car=("carries", "sum"), tgt=("targets", "sum"), g=("week", "nunique")).reset_index()

ranks = T.rank(ascending=False, method="min")
teams = []
for team, r in T.iterrows():
    rk = ranks.loc[team]
    tags = []
    if rk.pace <= 8: tags.append(("Fast pace", "Runs a lot of plays, so more fantasy chances"))
    if rk.pace >= 25: tags.append(("Slow pace", "Runs fewer plays than most teams"))
    if rk.proe <= 8: tags.append(("Pass-heavy", "Throws more than expected in normal game situations"))
    elif rk.proe >= 25: tags.append(("Run-first", "Runs more than expected in normal game situations"))
    else: tags.append(("Balanced", "Passes about as much as you'd expect"))
    if r.rb1Share >= 75: tags.append(("Feeds one back", "Lead RB gets most of the carries"))
    elif r.rb1Share <= 55: tags.append(("RB committee", "Carries are split between backs"))
    if rk.tgtRB <= 8: tags.append(("Throws to RBs", "Backs get a big share of targets"))
    if rk.tgtTE <= 6: tags.append(("TE-friendly", "Tight ends get a big share of targets"))
    if rk.adot <= 8: tags.append(("Pushes it deep", "Throws farther downfield than most"))
    if rk.adot >= 25: tags.append(("Quick, short passing", "Gets the ball out fast and short"))
    if rk.outside <= 8: tags.append(("Runs outside", "Lots of runs to the edges"))
    if rk.outside >= 25: tags.append(("Runs inside", "Mostly runs between the tackles"))
    if pd.notna(r.playAction) and rk.playAction <= 8: tags.append(("Lots of play-action", "Fakes the run often, which opens up receivers"))
    if pd.notna(r.motion) and rk.motion <= 8: tags.append(("Heavy motion", "Moves players before the snap to create mismatches"))
    keyp = pl[pl.team == team].sort_values("pts", ascending=False).head(4)
    teams.append({
        "team": team,
        "games": int(r.games),
        "m": {k: (None if pd.isna(v) else round(float(v), 2 if k == "epa" else 1)) for k, v in r.items() if k != "games"},
        "rk": {k: (None if pd.isna(v) else int(v)) for k, v in rk.items() if k != "games"},
        "tags": [{"t": a, "d": b} for a, b in tags],
        "players": [{"n": k.player_display_name, "pos": k.position, "ppg": round(k.pts / k.g, 1),
                     "carSh": round(100 * k.car / team_car[team], 1) if team_car[team] else 0,
                     "tgtSh": round(100 * k.tgt / team_tgt[team], 1) if team_tgt[team] else 0} for k in keyp.itertuples()],
    })

out = {"throughWeek": int(p.week.max()), "ftnWeek": ftn_week, "teams": teams,
       "lgAvg": {k: round(float(v), 2 if k == "epa" else 1) for k, v in T.mean().items() if k != "games"}}
with open(out_path, "w") as fh:
    json.dump(out, fh, separators=(",", ":"))
print(len(teams), "teams; pbp through week", out["throughWeek"], "; charting through week", ftn_week)
