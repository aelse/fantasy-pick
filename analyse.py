import sys, re

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
        return ( self.name == other.name and self.team == other.team and
            self.cost == other.cost and self.points == other.points )


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
        if not h.has_key(player.cost):
            h[player.cost] = []
        h[player.cost].append(player)
    culled_list = []
    for cost in sorted(h.keys(), reverse=True):
        sorted_by_points = sorted(h[cost], key=lambda x: x.points, reverse=True)
        culled_list = culled_list + sorted_by_points[:limit]
    num_after = len(culled_list)
    print 'Stripped %d players' % (num_before - num_after)
    return culled_list


def analyse():
    keepers     = get_players('goalkeepers')
    defenders   = get_players('defenders')
    midfielders = get_players('midfielders')
    forwards    = get_players('forwards')

    total_players = len(keepers) + len(defenders) + len(midfielders) + len(forwards)

    # Limited number of players in each position we can purchase.
    # As we're interested in the most points per cost, we can strip
    # out players that score less points than others at the same cost,
    # bearing in mind max number of players to purchase in a position.
    keepers     = cull_low_scorers(keepers, 2)
    defenders   = cull_low_scorers(defenders, 5)
    midfielders = cull_low_scorers(midfielders, 5)
    forwards    = cull_low_scorers(forwards, 3)

    new_total_players = len(keepers) + len(defenders) + len(midfielders) + len(forwards)

    print 'Retained %d total players of original %d' % (new_total_players,
    total_players)

    #print forwards

if __name__ == '__main__':
    analyse()
