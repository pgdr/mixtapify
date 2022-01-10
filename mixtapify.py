"""
        # keys: meta:dict, track:dict, bars:list, beats:list, sections:list, 'segments', 'tatums'])
        #
        # bars, beats, tatums: list of {'start':0, 'duration': 0, 'confidence': 1}
        #
        # sections: list of
        #
        # { 'start': 0.0, 'duration': 15.65056, 'confidence': 1.0,
        #   'loudness': -16.781, 'tempo': 117.503, 'tempo_confidence':
        #   0.905, 'key': 1, 'key_confidence': 0.353, 'mode': 1,
        #   'mode_confidence': 0.51, 'time_signature': 4,
        #   'time_signature_confidence': 1.0 }
        #
        # segments: list of
        #
        # { 'start': 0.0, 'duration': 0.28989, 'confidence': 0.0,
        #   'loudness_start': -60.0, 'loudness_max_time': 0.0,
        #   'loudness_max': -60.0, 'loudness_end': 0.0, 'pitches':
        #   [0.117, 0.147, 0.184, 0.327, 1.0, 0.205, 0.076, 0.218,
        #   0.102, 0.045, 0.064, 0.418], 'timbre': [0.0, 171.13, 9.469,
        #   -28.48, 57.491, -50.067, 14.833, 5.359, -27.228, 0.973,
        #   -10.64, -7.228]}
        #
        #
        # track: dict of 'num_samples', 'duration', 'sample_md5',
        #        'offset_seconds', 'window_seconds',
        #        'analysis_sample_rate', 'analysis_channels',
        #        'end_of_fade_in', 'start_of_fade_out', 'loudness',
        #        'tempo', 'tempo_confidence', 'time_signature',
        #        'time_signature_confidence', 'key', 'key_confidence',
        #        'mode', 'mode_confidence', 'codestring',
        #        'code_version', 'echoprintstring', 'echoprint_version',
        #        'synchstring', 'synch_version', 'rhythmstring',
        #        'rhythm_version'
"""

import spotipy
from pprint import pprint
from spotipy.oauth2 import SpotifyOAuth
import networkx as nx

# tsp = nx.approximation.traveling_salesman_problem
tsp = nx.algorithms.approximation.traveling_salesman.simulated_annealing_tsp

# scope = "user-library-modify playlist-modify-private playlist-modify-public"
scope = "playlist-read-collaborative"
S = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
USER = "pgdx"


def get_start_end(analysis):
    i = 0
    sect_start = analysis["sections"][i]
    while (
        sect_start["tempo"] == 0
        or sect_start["key_confidence"] < 0.2
        or sect_start["tempo_confidence"] < 0.2
    ):
        i += 1
        sect_start = analysis["sections"][i]
        print(i, sect_start)
    print(f"({i}", end=", ")

    i = -1
    sect_end = analysis["sections"][i]
    while (
        sect_end["tempo"] == 0
        or sect_end["key_confidence"] < 0.2
        or sect_end["tempo_confidence"] < 0.2
    ):
        i -= 1
        sect_end = analysis["sections"][i]
        print(i, sect_end)
    print(i, end=") ")
    print(
        f"[ {round(sect_end['key_confidence'],1)}, {round(sect_start['key_confidence'],1)}, {round(sect_end['tempo_confidence'],1)}, {round(sect_start['tempo_confidence'],1)}] ",
        end="",
    )
    return sect_start, sect_end


def analyse(playlist):
    # S.current_user_#unfollow_playlist#(playlist)
    playlist_name = playlist["name"]
    items_info = S.playlist_items(playlist["id"])
    items = items_info["items"]
    playlist_album = None

    max_tempo = -(10 ** 10)
    min_tempo = 10 ** 10
    max_loudness = -(10 ** 10)
    min_loudness = 10 ** 10

    analysis = {}
    for item in items:
        t = item["track"]
        t_name = t["name"]

        this = S.audio_analysis(t["id"])
        analysis[t_name] = this
        start, end = get_start_end(this)

        max_tempo = max(start["tempo"], end["tempo"], max_tempo)
        min_tempo = min(start["tempo"], end["tempo"], min_tempo)
        max_loudness = max(start["loudness"], end["loudness"], max_loudness)
        min_loudness = min(start["loudness"], end["loudness"], min_loudness)
        print(
            t_name,
            f"\n\ttempo: {start['tempo']}, {end['tempo']}\n\tloudness: {start['loudness']}, {end['loudness']}\n\tkey: {start['key']}, {end['key']}",
        )

    def norm_tempo(t):
        tempo = (t - min_tempo) / (max_tempo - min_tempo)
        return round(tempo, 2)

    def norm_loudness(t):
        loudness = (t - min_loudness) / (max_loudness - min_loudness)
        return round(loudness, 2)

    for item in analysis:
        this = analysis[item]
        start, end = get_start_end(this)
        start_t = norm_tempo(start["tempo"])
        end_t = norm_tempo(end["tempo"])
        start_l = norm_loudness(start["loudness"])
        end_l = norm_loudness(end["loudness"])
        start_k = start["key"]
        end_k = end["key"]

        retval = {
            "name": item,
            "tempo": (start_t, end_t),
            "loudness": (start_l, end_l),
            "key": (start_k, end_k),
        }
        print(
            f"{retval['name']}\n\ttempo: {retval['tempo']}\n\tloudness: {retval['loudness']}\n\tkey: {retval['key']}"
        )
        yield retval


def find_playlist(playlist_name):
    results = S.user_playlists(USER)
    playlists = results["items"]
    while results["next"]:
        results = S.next(results)
        playlists.extend(results["items"])

    for playlist in playlists:
        pname = playlist["name"]
        print(pname)
        if pname == playlist_name:
            return playlist


def mixtapify(nodes):
    D = nx.DiGraph()
    # directed graph
    for v in nodes:
        for u in nodes:
            if v == u:
                continue
            dt = abs(v["tempo"][1] - u["tempo"][0])
            dl = abs(v["loudness"][1] - u["loudness"][0])
            dk = 1 - v["key"][1] == u["key"][0]
            if v["key"][1] == -1:
                dk = 1

            D.add_edge(v["name"], u["name"], weight=sum([dt, dl, dk]))

    P = tsp(D, init_cycle="greedy", temp=1000, max_iterations=10000)
    cost = sum(D[n][nbr]["weight"] for n, nbr in nx.utils.pairwise(P))
    print("\n".join(str(node) for node in P))
    print(f"Cost: {cost}")
    return P


if __name__ == "__main__":
    from sys import argv

    if len(argv) < 2:
        exit("Usage: mixtapify playlist title goes here")
    pname = " ".join(argv[1:])
    playlist = find_playlist(pname)
    print(playlist["name"])
    nodes = list(analyse(playlist))
    path = mixtapify(nodes)
    for idx, node in enumerate(path):
        print((idx + 1), node)
