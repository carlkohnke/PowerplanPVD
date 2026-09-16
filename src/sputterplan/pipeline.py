"""High-level orchestration for the Python API."""

from __future__ import annotations

import numpy as np

from .configuration import PlanConfig
from .io import load_profile
from .physics import compute_physics
from .planner import create_schedule
from .results import CompositionProfile, PlanResult


def create_plan(config: PlanConfig, profile: CompositionProfile | None = None) -> PlanResult:
    """Validate inputs, calculate feasible powers, and create an operator schedule."""
    config.validate()
    loaded_profile = profile if profile is not None else load_profile(config)
    if loaded_profile.target_names != config.target_names:
        raise ValueError("Profile target order does not match the configuration target order.")
    physics = compute_physics(config, loaded_profile)
    schedule = create_schedule(config, loaded_profile, physics)
    return PlanResult(
        name=config.name,
        target_names=config.target_names,
        distance_nm=loaded_profile.distance_nm,
        desired_composition=loaded_profile.compositions,
        physics=physics,
        schedule=schedule,
        operation_strategy=config.operation.strategy,
        target_rates_nm_per_min_per_watt=np.asarray(
            [target.rate_nm_per_min_per_watt for target in config.targets],
            dtype=float,
        ),
    )
