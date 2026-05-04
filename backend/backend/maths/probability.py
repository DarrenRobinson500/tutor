from math import comb, factorial
from itertools import product

def nCr(n, r):
    return comb(n, r)

def nPr(n, r):
    return factorial(n) // factorial(n - r)

def ways_sum(dice, target):
    count = 0
    for outcome in product(range(1, 7), repeat=dice):
        if sum(outcome) == target:
            count += 1
    return count

def hypergeom(N, K, n, k):
    return comb(K, k) * comb(N - K, n - k) / comb(N, n)

