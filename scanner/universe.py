
from collections import defaultdict

def build_universe(orderbooks):

    universe = defaultdict(list)

    for ob in orderbooks:
        if not ob:
            continue
        universe[ob["symbol"]].append(ob)

    return universe
