"""Independent Dijkstra oracle used only for small test instances."""

from heapq import heappop, heappush
from itertools import combinations


def minimum(durations: tuple[int, ...], capacity: int) -> int | None:
    if not durations:
        return 0
    full = (1 << len(durations)) - 1
    distances = {(full, 0): 0}
    queue = [(0, full, 0)]
    while queue:
        elapsed, bank_a, side = heappop(queue)
        if elapsed != distances[bank_a, side]:
            continue
        if bank_a == 0:
            return elapsed
        available = [i for i in range(len(durations)) if bool(bank_a & (1 << i)) == (side == 0)]
        for count in range(1, min(capacity, len(available)) + 1):
            for passengers in combinations(available, count):
                moved = sum(1 << i for i in passengers)
                state = (bank_a ^ moved, 1 - side)
                cost = elapsed + max(durations[i] for i in passengers)
                if state not in distances or cost < distances[state]:
                    distances[state] = cost
                    heappush(queue, (cost, *state))
    return None
