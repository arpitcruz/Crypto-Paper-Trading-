"""A collection of classic recursion algorithms in pure Python 3.11.

Every recursive function is built from the same two ingredients:

* **Base case** - the smallest input the function can answer *directly*,
  without calling itself.  It is what stops the recursion.  A function
  without a reachable base case recurses forever and Python eventually
  raises ``RecursionError``.
* **Recursive case** - the function calls itself on a *strictly smaller*
  sub-problem and combines that answer with a little extra work.  "Strictly
  smaller" is what guarantees the base case is eventually reached.

For example ``factorial``::

    base case:       0! = 1! = 1
    recursive case:  n! = n * (n - 1)!      (n > 1)

Each function below documents its own recurrence and base case in its
docstring.  Only the standard library is used.

Note on recursion depth: CPython's default recursion limit is 1000 frames,
so the linearly-recursive helpers here (``factorial``, ``sum_digits``,
``reverse_string``, ``fibonacci_memo``, ...) raise ``RecursionError`` for
inputs of roughly a thousand or more.  That is a deliberate property of the
teaching implementations - iterative versions would not have the limit.

Run ``python3 recursion.py`` for a short demo of every function.
"""

from __future__ import annotations

__all__ = [
    "factorial",
    "fibonacci",
    "fibonacci_memo",
    "gcd",
    "power",
    "sum_digits",
    "reverse_string",
    "is_palindrome",
    "binary_search",
    "flatten",
    "permutations",
    "hanoi",
    "ackermann",
    "merge_sort",
]


# --------------------------------------------------------------------------
# Numeric recursion
# --------------------------------------------------------------------------
def factorial(n: int) -> int:
    """Return ``n!`` computed recursively.

    Base case:      ``factorial(0) == factorial(1) == 1``
    Recursive case: ``factorial(n) == n * factorial(n - 1)``

    Raises:
        TypeError: if *n* is not an ``int``.
        ValueError: if *n* is negative.
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an int, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if n <= 1:  # base case
        return 1
    return n * factorial(n - 1)  # recursive case


def fibonacci(n: int) -> int:
    """Return the *n*-th Fibonacci number by naive double recursion.

    Base case:      ``fibonacci(0) == 0``, ``fibonacci(1) == 1``
    Recursive case: ``fibonacci(n) == fibonacci(n - 1) + fibonacci(n - 2)``

    This is the textbook exponential version: it costs **O(2**n)** calls
    because the same sub-problems are recomputed over and over.  Use
    :func:`fibonacci_memo` for anything beyond ``n`` of about 30.

    Raises:
        TypeError: if *n* is not an ``int``.
        ValueError: if *n* is negative.
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an int, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if n < 2:  # base case
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)  # recursive case


def fibonacci_memo(n: int, memo: dict[int, int] | None = None) -> int:
    """Return the *n*-th Fibonacci number in **O(n)** time using memoization.

    Base case:      ``fibonacci_memo(0) == 0``, ``fibonacci_memo(1) == 1``
    Recursive case: ``f(n) == f(n - 1) + f(n - 2)``, with every result cached
                    in *memo* so each sub-problem is solved exactly once.

    Args:
        n: index of the wanted Fibonacci number.
        memo: optional cache, mutated in place.  A fresh ``dict`` is created
            when omitted, so callers never share state by accident.

    Raises:
        TypeError: if *n* is not an ``int`` or *memo* is not a ``dict``/None.
        ValueError: if *n* is negative.
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an int, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if memo is None:
        memo = {}
    elif not isinstance(memo, dict):
        raise TypeError(f"memo must be a dict or None, got {type(memo).__name__}")
    if n < 2:  # base case
        return n
    if n in memo:  # already solved
        return memo[n]
    memo[n] = fibonacci_memo(n - 1, memo) + fibonacci_memo(n - 2, memo)
    return memo[n]


def gcd(a: int, b: int) -> int:
    """Return the greatest common divisor of *a* and *b* (Euclid's algorithm).

    Base case:      ``gcd(a, 0) == abs(a)``
    Recursive case: ``gcd(a, b) == gcd(b, a % b)``

    Signs are ignored, so ``gcd(-12, 18) == 6``.  By convention
    ``gcd(0, 0) == 0``.

    Raises:
        TypeError: if *a* or *b* is not an ``int``.
    """
    if not isinstance(a, int) or not isinstance(b, int):
        raise TypeError("a and b must both be ints")
    a, b = abs(a), abs(b)
    if b == 0:  # base case
        return a
    return gcd(b, a % b)  # recursive case


def power(base: float, exp: int) -> float:
    """Return ``base ** exp`` by fast exponentiation (squaring).

    Base case:      ``power(base, 0) == 1.0``
    Recursive case: ``power(base, exp) == power(base * base, exp // 2)`` when
                    *exp* is even, and ``base * power(base, exp - 1)`` when it
                    is odd.  Negative exponents use
                    ``power(base, -exp) -> 1 / result``.

    This runs in **O(log exp)** multiplications.  The result is always a
    ``float`` (``power(2, 10) == 1024.0``).

    Raises:
        TypeError: if *base* is not a real number or *exp* is not an ``int``.
        ZeroDivisionError: if *base* is 0 and *exp* is negative.
    """
    if isinstance(base, bool) or not isinstance(base, (int, float)):
        raise TypeError(f"base must be an int or float, got {type(base).__name__}")
    if not isinstance(exp, int) or isinstance(exp, bool):
        raise TypeError(f"exp must be an int, got {type(exp).__name__}")
    if exp < 0:
        if base == 0:
            raise ZeroDivisionError("0.0 cannot be raised to a negative power")
        return 1.0 / power(base, -exp)
    if exp == 0:  # base case
        return 1.0
    half = power(base, exp // 2)
    if exp % 2 == 0:
        return half * half
    return float(base) * half * half


def sum_digits(n: int) -> int:
    """Return the sum of the decimal digits of a non-negative integer.

    Base case:      ``sum_digits(n) == n`` for a single digit (``n < 10``)
    Recursive case: ``sum_digits(n) == n % 10 + sum_digits(n // 10)``

    Raises:
        TypeError: if *n* is not an ``int``.
        ValueError: if *n* is negative.
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an int, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if n < 10:  # base case
        return n
    return n % 10 + sum_digits(n // 10)  # recursive case


def ackermann(m: int, n: int) -> int:
    """Return the Ackermann function ``A(m, n)``.

    Base cases / recursive cases::

        A(0, n) = n + 1
        A(m, 0) = A(m - 1, 1)                 (m > 0)
        A(m, n) = A(m - 1, A(m, n - 1))       (m > 0, n > 0)

    It is the classic example of a total computable function that is *not*
    primitive recursive: it grows so fast that ``A(4, 2)`` already has 19729
    digits.  In practice anything with ``m >= 4`` blows CPython's recursion
    limit (``RecursionError``).

    Raises:
        TypeError: if *m* or *n* is not an ``int``.
        ValueError: if *m* or *n* is negative.
    """
    if not isinstance(m, int) or not isinstance(n, int):
        raise TypeError("m and n must both be ints")
    if m < 0 or n < 0:
        raise ValueError(f"m and n must be non-negative, got m={m}, n={n}")
    if m == 0:  # base case
        return n + 1
    if n == 0:
        return ackermann(m - 1, 1)
    return ackermann(m - 1, ackermann(m, n - 1))


# --------------------------------------------------------------------------
# String recursion
# --------------------------------------------------------------------------
def reverse_string(s: str) -> str:
    """Return *s* reversed, one character per recursive call.

    Base case:      the empty string (and any single character) reverses to
                    itself.
    Recursive case: ``reverse_string(s) == reverse_string(s[1:]) + s[0]``

    Raises:
        TypeError: if *s* is not a ``str``.
    """
    if not isinstance(s, str):
        raise TypeError(f"s must be a str, got {type(s).__name__}")
    if len(s) <= 1:  # base case
        return s
    return reverse_string(s[1:]) + s[0]  # recursive case


def is_palindrome(s: str) -> bool:
    """Return ``True`` if *s* reads the same forwards and backwards.

    Comparison is case-insensitive and every non-alphanumeric character is
    ignored, so ``"A man, a plan, a canal: Panama"`` is a palindrome.  The
    empty string (and any string with no alphanumeric characters) counts as a
    palindrome.

    Base case:      strings of length 0 or 1 are palindromes.
    Recursive case: first and last characters must match *and* the inner
                    slice must itself be a palindrome.

    Raises:
        TypeError: if *s* is not a ``str``.
    """
    if not isinstance(s, str):
        raise TypeError(f"s must be a str, got {type(s).__name__}")
    cleaned = "".join(ch for ch in s.lower() if ch.isalnum())
    return _is_palindrome_clean(cleaned)


def _is_palindrome_clean(s: str) -> bool:
    """Recursive core of :func:`is_palindrome` on already-normalised text."""
    if len(s) <= 1:  # base case
        return True
    if s[0] != s[-1]:
        return False
    return _is_palindrome_clean(s[1:-1])  # recursive case


# --------------------------------------------------------------------------
# List / structural recursion
# --------------------------------------------------------------------------
def binary_search(
    arr: list[int], target: int, low: int = 0, high: int | None = None
) -> int:
    """Return the index of *target* in the **sorted** list *arr*, or ``-1``.

    Base case:      ``low > high`` means the window is empty -> not found
                    (``-1``); or the middle element equals *target*.
    Recursive case: search the left half when the middle element is too big,
                    the right half when it is too small.  **O(log n)**.

    Args:
        arr: list sorted in ascending order (unsorted input gives undefined
            results, it is not validated).
        target: value to look for.
        low: inclusive left bound of the search window.
        high: inclusive right bound; defaults to ``len(arr) - 1``.

    When duplicates are present, *some* matching index is returned - not
    necessarily the first one.

    Raises:
        TypeError: if *arr* is not a ``list`` or the bounds are not ``int``.
    """
    if not isinstance(arr, list):
        raise TypeError(f"arr must be a list, got {type(arr).__name__}")
    if high is None:
        high = len(arr) - 1
    if not isinstance(low, int) or not isinstance(high, int):
        raise TypeError("low and high must be ints")
    if low > high:  # base case: empty window
        return -1
    mid = (low + high) // 2
    if arr[mid] == target:  # base case: found
        return mid
    if arr[mid] > target:
        return binary_search(arr, target, low, mid - 1)
    return binary_search(arr, target, mid + 1, high)


def flatten(nested: list) -> list:
    """Flatten an arbitrarily nested list into a single flat list.

    Base case:      a non-list element is appended as-is; the empty list
                    flattens to ``[]``.
    Recursive case: a nested list is flattened first, then extended onto the
                    result.

    Only ``list`` instances are descended into - tuples, sets, strings and
    dicts are treated as plain values and kept intact.  The input is never
    mutated; a new list is returned.

    Raises:
        TypeError: if *nested* is not a ``list``.
    """
    if not isinstance(nested, list):
        raise TypeError(f"nested must be a list, got {type(nested).__name__}")
    flat: list = []
    for item in nested:
        if isinstance(item, list):
            flat.extend(flatten(item))  # recursive case
        else:
            flat.append(item)  # base case
    return flat


def permutations(items: list) -> list[list]:
    """Return every ordering of *items* as a list of new lists.

    Base case:      ``permutations([]) == [[]]`` - exactly one way to arrange
                    nothing.
    Recursive case: for each position *i*, take ``items[i]`` as the first
                    element and prepend it to every permutation of the
                    remaining elements.

    There are ``len(items)!`` results, produced in the standard
    "first element varies slowest" order (lexicographic with respect to the
    input positions).  Duplicate values yield duplicate permutations; the
    input list is not mutated.

    Raises:
        TypeError: if *items* is not a ``list``.
    """
    if not isinstance(items, list):
        raise TypeError(f"items must be a list, got {type(items).__name__}")
    if len(items) <= 1:  # base case
        return [list(items)]
    result: list[list] = []
    for i, item in enumerate(items):
        rest = items[:i] + items[i + 1:]
        for perm in permutations(rest):  # recursive case
            result.append([item] + perm)
    return result


def merge_sort(arr: list) -> list:
    """Return a new sorted list containing the elements of *arr*.

    Base case:      a list of 0 or 1 elements is already sorted.
    Recursive case: sort each half, then merge the two sorted halves.
                    **O(n log n)** time, stable, and the input list is left
                    untouched.

    Elements must be mutually comparable with ``<=``; otherwise the usual
    ``TypeError`` from the comparison propagates.

    Raises:
        TypeError: if *arr* is not a ``list``.
    """
    if not isinstance(arr, list):
        raise TypeError(f"arr must be a list, got {type(arr).__name__}")
    if len(arr) <= 1:  # base case
        return list(arr)
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])  # recursive case
    right = merge_sort(arr[mid:])
    return _merge(left, right)


def _merge(left: list, right: list) -> list:
    """Merge two sorted lists into one sorted list (stable)."""
    merged: list = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:  # <= keeps the sort stable
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


# --------------------------------------------------------------------------
# Towers of Hanoi
# --------------------------------------------------------------------------
def hanoi(
    n: int, source: str = "A", target: str = "C", auxiliary: str = "B"
) -> list[tuple[str, str]]:
    """Return the moves that solve the Towers of Hanoi for *n* disks.

    Base case:      ``n == 0`` -> no moves at all (``[]``).
    Recursive case: move ``n - 1`` disks *source -> auxiliary*, move the
                    largest disk *source -> target*, then move the ``n - 1``
                    disks *auxiliary -> target*.

    Returns:
        A list of ``(from_peg, to_peg)`` tuples in the order they must be
        played.  Its length is always ``2 ** n - 1``.

    Raises:
        TypeError: if *n* is not an ``int`` or a peg name is not a ``str``.
        ValueError: if *n* is negative.
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an int, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if not all(isinstance(peg, str) for peg in (source, target, auxiliary)):
        raise TypeError("peg names must be strings")
    if n == 0:  # base case
        return []
    moves = hanoi(n - 1, source, auxiliary, target)
    moves.append((source, target))
    moves.extend(hanoi(n - 1, auxiliary, target, source))
    return moves


# --------------------------------------------------------------------------
# Demo
# --------------------------------------------------------------------------
def _demo() -> None:
    """Print one short example of every public function."""
    print("factorial(6)               ->", factorial(6))
    print("fibonacci(10)              ->", fibonacci(10), "(naive, O(2**n))")
    print("fibonacci_memo(50)         ->", fibonacci_memo(50), "(memoized, O(n))")
    print("gcd(-48, 18)               ->", gcd(-48, 18))
    print("power(2, 10)               ->", power(2, 10))
    print("power(2, -3)               ->", power(2, -3))
    print("sum_digits(98765)          ->", sum_digits(98765))
    print("reverse_string('recursion')->", reverse_string("recursion"))
    print(
        "is_palindrome('A man, a plan, a canal: Panama') ->",
        is_palindrome("A man, a plan, a canal: Panama"),
    )
    print("binary_search([1,3,5,7,9,11], 7) ->", binary_search([1, 3, 5, 7, 9, 11], 7))
    print("binary_search([1,3,5,7,9,11], 4) ->", binary_search([1, 3, 5, 7, 9, 11], 4))
    print("flatten([1, [2, [3, [4]], 5]]) ->", flatten([1, [2, [3, [4]], 5]]))
    print("permutations([1, 2, 3])    ->", permutations([1, 2, 3]))
    print("hanoi(3)                   ->", hanoi(3))
    print("  -> moves:", len(hanoi(3)), "== 2**3 - 1")
    print("ackermann(2, 3)            ->", ackermann(2, 3))
    unsorted = [5, 2, 9, 1, 5, 6]
    print("merge_sort([5,2,9,1,5,6]) ->", merge_sort(unsorted), "(input:", unsorted, ")")


if __name__ == "__main__":
    _demo()
