import pstats
from pstats import SortKey

p = pstats.Stats("results.profile")
p.sort_stats(SortKey.CUMULATIVE).print_stats()
