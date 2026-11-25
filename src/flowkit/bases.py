"""Named base models. Each entry is a factory `seed -> estimator`; names are what spec strings and command lines use."""
from models import SoftVote, task2_model


def softvote_balanced(seed):
    """RF + ExtraTrees + LightGBM, mean probability, balanced class weights (production base since 004)."""
    return SoftVote(seed=seed)


def softvote_unweighted(seed):
    return SoftVote(seed=seed, class_weight=None)


BASES = {"softvote": softvote_balanced, "softvote_unweighted": softvote_unweighted, "task2_production": task2_model}


def make_base(name, seed):
    if name not in BASES:
        raise ValueError(f"unknown base {name!r}; choose from {sorted(BASES)}")
    return BASES[name](seed)
