"""Trip states and binary time sums encoded as CNF."""

from pysat.card import CardEnc
from pysat.formula import IDPool

from .model import Limits, SearchLimitExceeded

type Literal = int | bool


def negate(literal: Literal) -> Literal:
    return not literal if type(literal) is bool else -literal


def crossing_bounds(durations: tuple[int, ...], capacity: int) -> tuple[int, int, int]:
    ordered = sorted(durations, reverse=True)
    cover_cost = sum(ordered[::capacity])
    groups = (len(durations) + capacity - 1) // capacity
    minimum_steps = 2 * ((len(durations) - 2) // (capacity - 1) + 1) - 1
    return cover_cost, groups, minimum_steps


class Formula:
    def __init__(self, limits: Limits):
        self.pool = IDPool()
        self.clauses: list[list[int]] = []
        self.limits = limits

    def check_size(self) -> None:
        if self.pool.top > self.limits.max_variables:
            raise SearchLimitExceeded("SAT variable limit reached")
        if len(self.clauses) > self.limits.max_clauses:
            raise SearchLimitExceeded("SAT clause limit reached")

    def variable(self) -> int:
        result = self.pool.id()
        self.check_size()
        return result

    def add(self, *literals: Literal) -> None:
        clause: set[int] = set()
        for literal in literals:
            if literal is True:
                return
            if literal is False:
                continue
            if -literal in clause:
                return
            clause.add(literal)
        self.clauses.append(sorted(clause))
        self.check_size()

    def at_most(self, literals: list[int], bound: int) -> None:
        if bound >= len(literals):
            return
        encoded = CardEnc.atmost(literals, bound=bound, vpool=self.pool)
        self.clauses.extend(encoded.clauses)
        self.check_size()

    def either(self, literals: list[Literal]) -> Literal:
        if any(value is True for value in literals):
            return True
        values = {value for value in literals if value is not False}
        if any(-value in values for value in values):
            return True
        if not values:
            return False
        if len(values) == 1:
            return next(iter(values))
        result = self.variable()
        self.add(-result, *values)
        for value in sorted(values):
            self.add(result, -value)
        return result

    def both(self, left: Literal, right: Literal) -> Literal:
        if left is False or right is False:
            return False
        if left is True:
            return right
        if right is True or left == right:
            return left
        if left == -right:
            return False
        result = self.variable()
        self.add(-result, left)
        self.add(-result, right)
        self.add(result, -left, -right)
        return result

    def xor(self, left: Literal, right: Literal) -> Literal:
        if left is False:
            return right
        if right is False:
            return left
        if left is True:
            return negate(right)
        if right is True:
            return negate(left)
        if left == right:
            return False
        if left == -right:
            return True
        result = self.variable()
        self.add(-left, -right, -result)
        self.add(left, right, -result)
        self.add(left, -right, result)
        self.add(-left, right, result)
        return result

    def add_bits(self, left: list[Literal], right: list[Literal]) -> list[Literal]:
        carry: Literal = False
        result = []
        for a, b in zip(left, right, strict=True):
            pair = self.xor(a, b)
            result.append(self.xor(pair, carry))
            carry = self.either([self.both(a, b), self.both(pair, carry)])
        self.add(negate(carry))
        return result

    def bound_bits(self, bits: list[Literal], bound: int) -> None:
        for index, bit in enumerate(bits):
            if not (bound >> index) & 1:
                higher_differ = [
                    negate(bits[j]) if (bound >> j) & 1 else bits[j]
                    for j in range(index + 1, len(bits))
                ]
                self.add(negate(bit), *higher_differ)


class Encoding:
    def __init__(self, durations: tuple[int, ...], capacity: int, deadline: int, limits: Limits):
        n = len(durations)
        # Removing a repeated state never increases cost, including zero-cost loops.
        steps = (1 << (n + 1)) - 1
        cover_cost, groups, minimum_steps = crossing_bounds(durations, capacity)
        if min(durations) > 0:
            # Every trip costs at least the fastest time. Covering all passengers
            # also requires the maxima of their cheapest capacity-sized groups.
            steps = min(steps, (deadline - cover_cost) // min(durations) + groups)
        if steps % 2 == 0:
            steps -= 1
        self.formula = Formula(limits)
        self.active: list[int] = []
        self.moves: list[list[int]] = []
        if steps < minimum_steps or deadline < cover_cost:
            self.formula.add()
            return
        if (steps + 1) * n + steps * (n + 1) > limits.max_variables:
            raise SearchLimitExceeded("trip horizon exceeds the SAT variable limit")
        f = self.formula
        positions = [[f.variable() for _ in durations] for _ in range(steps + 1)]
        self.active = [f.variable() for _ in range(steps)]
        self.moves = [[f.variable() for _ in durations] for _ in range(steps)]
        for variable in positions[0]:
            f.add(variable)
        for variable in positions[-1]:
            f.add(-variable)
        for variable in self.active[:minimum_steps]:
            f.add(variable)
        for previous, following in zip(self.active, self.active[1:]):
            f.add(previous, -following)

        costs = sorted(set(durations))
        width = max(1, deadline.bit_length())
        total: list[Literal] = [False] * width
        for step, (active, moves) in enumerate(zip(self.active, self.moves, strict=True)):
            f.add(-active, *moves)
            f.at_most(moves, capacity)
            for passenger, move in enumerate(moves):
                f.add(-move, active)
                current, following = positions[step][passenger], positions[step + 1][passenger]
                f.add(-move, current if step % 2 == 0 else -current)
                switched = f.xor(current, move)
                f.add(-following, switched)
                f.add(following, negate(switched))

            choices = [f.variable() for _ in costs]
            f.add(-active, *choices)
            f.at_most(choices, 1)
            for cost, choice in zip(costs, choices, strict=True):
                f.add(-choice, active)
                f.add(-choice, *[m for m, d in zip(moves, durations) if d == cost])
                for move, duration in zip(moves, durations, strict=True):
                    if duration > cost:
                        f.add(-choice, -move)
            bits = [
                f.either([choice for cost, choice in zip(costs, choices) if (cost >> bit) & 1])
                for bit in range(width)
            ]
            total = f.add_bits(total, bits)
        f.bound_bits(total, deadline)
