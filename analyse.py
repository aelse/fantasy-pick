import re
import sys
from multiprocessing import Pool


class PlayerSet(object):
    def __init__(self, player_list):
        self.player_list = player_list
        self.cost = sum(map(lambda x: x.cost, player_list))
        self.points = sum(map(lambda x: x.points, player_list))

    def __repr__(self):
        return 'PlayerSet([' + ', '.join(map(repr, self.player_list)) + '])'


class Player(object):

    def __init__(self, name, team, cost, points):
        self.name = name
        self.team = team
        self.cost = float(cost)
        self.points = int(points)

        # premium is player cost above 4 mil
        self.premium = cost - 4.0

    def __repr__(self):
        return 'Player("%s", "%s", %.1f, %d)' % (self.name, self.team,
            self.cost, self.points)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return (self.name == other.name and self.team == other.team and
            self.cost == other.cost and self.points == other.points)


def parse_player_record(record):
    player = None
    m = re.match('^\s*(\S.*\S+)\s+([A-Z]{3})\s+(\d+\.\d)\s+(\d+)', record)
    if m:
        name = m.group(1)
        team = m.group(2)
        cost = float(m.group(3))
        points = int(m.group(4))
        player = Player(name, team, cost, points)
    else:
        print 'Invalid player record "%s"' % record
        raise
    return player


def get_players(players_file):
    players = []
    fh = open(players_file, 'r')
    records = fh.readlines()
    for record in records:
        player = parse_player_record(record)
        players.append(player)
    print 'Got %d players from %s' % (len(players), players_file)
    return players


def cull_low_scorers(players, limit):
    # limit is number of high scorers to retain in a price bracket
    num_before = len(players)
    h = {}
    for player in players:
        if player.cost not in h:
            h[player.cost] = []
        h[player.cost].append(player)
    culled_list = []
    for cost in sorted(h.keys(), reverse=True):
        sorted_by_points = sorted(h[cost],
            key=lambda x: x.points, reverse=True)
        culled_list = culled_list + sorted_by_points[:limit]
    num_after = len(culled_list)
    print 'Stripped %d players' % (num_before - num_after)
    return culled_list


def nchoosek(items, n):
    if n == 0:
        yield []
    else:
        for (i, item) in enumerate(items):
            for cc in nchoosek(items[i + 1:], n - 1):
                yield [item] + cc


def analyse():
    keepers = get_players('goalkeepers')
    defenders = get_players('defenders')
    midfielders = get_players('midfielders')
    forwards = get_players('forwards')

    total_players = len(keepers + defenders + midfielders + forwards)

    # Limited number of players in each position we can purchase.
    # As we're interested in the most points per cost, we can strip
    # out players that score less points than others at the same cost,
    # bearing in mind max number of players to purchase in a position.
    # It is possible that higher scorers would not be eligible in a
    # particular team due to max 3 from same side, thus opening the
    # door to lower scorers, but we choose to ignore this as a
    # compromise.
    keepers = cull_low_scorers(keepers, 2)
    #defenders = cull_low_scorers(defenders, 5)
    #midfielders = cull_low_scorers(midfielders, 5)
    defenders = cull_low_scorers(defenders, 3)
    midfielders = cull_low_scorers(midfielders, 2)
    #forwards = cull_low_scorers(forwards, 3)

    new_total_players = len(keepers + defenders + midfielders + forwards)
    print 'Retained %d total players of original %d' % (new_total_players,
        total_players)

    # Seed the generator with our pre-selected keepers
    #keepers = [Player("Vorm", "SWA", 5.5, 158), Player("Federici", "RDG", 4.5, 0)]
    keepers = [Player("Vorm", "SWA", 5.5, 158), Player("Al-Habsi", "WIG", 5.0, 138)]

    # Generate all combinations for each position
    c_defenders = list(nchoosek(defenders, 5))
    c_midfielders = list(nchoosek(midfielders, 5))
    c_forwards = list(nchoosek(forwards, 3))

    print '%d defender, %d midfielder and %d forward combinations' % (
        len(c_defenders), len(c_midfielders), len(c_forwards))

    # Constraint - require some specific players
    #required = [Player("Van Persie", "ARS", 13.0, 269), Player("Cisse", "NEW", 9.5, 105), Player("Le Fondre", "RDG", 5.0, 0)]
    required = [Player("Aguero", "MCI", 11.5, 211), Player("Cisse",
        "NEW", 9.5, 105)]
    #, Player("Le Fondre", "RDG", 5.0, 0)]
    for p in required:
        c_forwards = filter(lambda x: p in x, c_forwards)

    #required = [Player("Sinclair", "SWA", 7.0, 151)]
    required = [Player("Sinclair", "SWA", 7.0, 151),
        Player("Moses", "WIG", 7.0, 140), Player("Walters", "STO", 6.5, 140)]
    for p in required:
        c_midfielders = filter(lambda x: p in x, c_midfielders)

    required = [Player("Simpson", "NEW", 5.0, 117)]
    for p in required:
        c_defenders = filter(lambda x: p in x, c_defenders)

    print 'Position constraints applied. %d defender, %d midfielder and %d forward combinations remain' % (len(c_defenders), len(c_midfielders), len(c_forwards))

    # Constraint - limit amount we can spend in total on a position
    c_forwards = filter(lambda x: sum(map(lambda y: y.cost, x)) <= 30, c_forwards)
    c_defenders = filter(lambda x: sum(map(lambda y: y.cost, x)) <= 35, c_defenders)
    print 'Price constraints applied. %d defender, %d midfielder and %d forward combinations remain' % (
        len(c_defenders), len(c_midfielders), len(c_forwards))

    print 'Picking from %d defender, %d midfielder and %d forward choices' % (
        len(c_defenders), len(c_midfielders), len(c_forwards))

    budget = 100.0
    keeper_points = sum(map(lambda x: x.points, keepers))
    keeper_cost = sum(map(lambda x: x.cost, keepers))

    best_team = None
    best_team_cost = 0.0
    best_team_points = 0

    f_count = 0
    f_total = len(c_forwards)

    pool = Pool(processes=4)

    for f in c_forwards:
        f_count += 1
        print 'Round %d/%d' % (f_count, f_total)
        fixed = f + keepers
        h = map(lambda x: {'fixed': fixed + x, 'defenders': c_defenders},
                c_midfielders)
        results = pool.map(best_combo, h)
        for ps in results:
            if ps and ps.points > best_team_points:
                best_team = ps
                best_team_points = ps.points
                best_team_cost = ps.cost
                print '==============\nNew best team. Cost %f, points %d' % (
                    best_team_cost, best_team_points)
                print best_team
    print '==============\nFinal best team. Cost %f, points %d' % (
        best_team_cost, best_team_points)
    print best_team


def best_combo(h):
    fixed_members = h['fixed']
    defenders = h['defenders']

    best_team = None
    best_team_points = 0
    budget = 100.0
    for d in defenders:
        ps = PlayerSet(fixed_members + d)
        if ps.cost <= budget and ps.points > best_team_points:
            # Ensure no more than 3 players from any team
            teams = {}
            for player in ps.player_list:
                try:
                    teams[player.team] += 1
                except KeyError:
                    teams[player.team] = 1
            too_many_players = len(filter(lambda x: x > 3, teams.values()))
            if not too_many_players:
                best_team = ps
                best_team_points = ps.points
        #else: print '%f > %f' % (ps.cost, budget)
    return best_team


if __name__ == '__main__':
    analyse()
