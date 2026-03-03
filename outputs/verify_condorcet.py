import math


def majority_correct_probability(n: int, p: float) -> float:
    if n <= 0 or n % 2 == 0:
        raise ValueError("n must be a positive odd integer")
    if not (0.0 <= p <= 1.0):
        raise ValueError("p must be between 0 and 1")

    k_min = n // 2 + 1
    return sum(math.comb(n, k) * (p**k) * ((1 - p) ** (n - k)) for k in range(k_min, n + 1))


def main() -> None:
    p = 0.70
    for n in (5, 11):
        prob = majority_correct_probability(n=n, p=p)
        print(f"n={n}, p={p:.2f} -> P(majority correct)={prob:.12f} ({prob*100:.6f}%)")


if __name__ == "__main__":
    main()

