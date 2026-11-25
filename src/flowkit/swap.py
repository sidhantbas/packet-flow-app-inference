"""Count-preserving consensus pair swap: where the labels say a but another view says b, and other flows say b while that view
says a, exchange their labels in pairs (most confident first). Class counts never change."""
import numpy as np


def consensus_pair_swap(labels, other, other_proba, classes):
    """Returns (new labels, list of swapped index pairs). other_proba: the other view's probabilities, columns in `classes`."""
    out = np.asarray(labels, dtype=object).copy()
    other = np.asarray(other, dtype=object)
    col = {c: k for k, c in enumerate(classes)}
    swaps = []
    for i, a in enumerate(classes):
        for b in classes[i + 1:]:
            A = np.flatnonzero((out == a) & (other == b))
            B = np.flatnonzero((out == b) & (other == a))
            k = min(len(A), len(B))
            if not k:
                continue
            A = A[np.argsort(-other_proba[A, col[b]], kind="stable")][:k]
            B = B[np.argsort(-other_proba[B, col[a]], kind="stable")][:k]
            for p, q in zip(A, B):
                out[p], out[q] = b, a
                swaps.append((int(p), int(q)))
    return out, swaps
