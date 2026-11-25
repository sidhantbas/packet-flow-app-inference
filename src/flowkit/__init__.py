"""flowkit: small reusable components for decision pipelines (first used in experiment 102).

Modules
  bases        named base models (`make_base("softvote", seed)`)
  calibration  probability calibration on cross-validated probabilities (`calibrated(factory, "sigmoid", seed)`)
  counts       count-constrained labelling (`quota_assign`, `share_counts`)
  pipeline     `DecisionPipeline`: base -> calibration -> labels, configured by keyword or by a spec string

A spec string composes a pipeline without new code, e.g. "base=softvote,cal=sigmoid,counts=shares".
Runners import from here; experiment-specific logic stays in the runner (src/expNNN_*.py).
"""
from .pipeline import DecisionPipeline, from_spec

__all__ = ["DecisionPipeline", "from_spec"]
