"""High-level orchestration for the Python API."""

from __future__ import annotations

import numpy as np

from .configuration import PlanConfig
from .errors import ProfileError
from .io import load_profile
from .physics import compute_physics
from .planner import create_schedule
from .results import CompositionProfile, PlanResult


def _validate_supplied_profile(
    profile: CompositionProfile, config: PlanConfig
) -> CompositionProfile:
    """Validate public-API profile inputs, which do not pass through the file reader."""
    try:
        distance = np.asarray(profile.distance_nm, dtype=float)
        compositions = np.asarray(profile.compositions, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ProfileError("Profile distances and compositions must be numeric arrays.") from exc
    if profile.target_names != config.target_names:
        raise ProfileError("Profile target order does not match the configuration target order.")
    if distance.ndim != 1 or distance.size < 2:
        raise ProfileError("The composition profile must contain at least two distance points.")
    if compositions.shape != (distance.size, len(config.targets)):
        raise ProfileError("Composition table dimensions do not match the configured targets.")
    if not np.all(np.isfinite(distance)) or not np.all(np.isfinite(compositions)):
        raise ProfileError("Distance and composition values must be finite.")
    if np.any(np.diff(distance) <= 0):
        raise ProfileError("Distance must increase strictly.")
    if np.any(compositions < 0):
        raise ProfileError("Composition values cannot be negative.")
    totals = np.sum(compositions, axis=1)
    if np.any(np.abs(totals - 1.0) > config.profile.composition_sum_tolerance):
        raise ProfileError("Every supplied profile composition row must sum to one.")
    return CompositionProfile(distance, compositions, profile.target_names)


def create_plan(config: PlanConfig, profile: CompositionProfile | None = None) -> PlanResult:
    """Validate inputs, calculate feasible powers, and create an operator schedule."""
    config.validate()
    loaded_profile = (
        load_profile(config) if profile is None else _validate_supplied_profile(profile, config)
    )
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
