# learning/services/ai_srs.py
"""
AI SRS scheduler (offline, no external services).

What it does
- Learns a per-user ability (theta) and a per-card difficulty (ai_difficulty)
  with an online logistic update after every review.
- Maintains a memory half-life per card (half_life_days).
- Chooses the next interval so the predicted recall probability at review time
  is close to a target (default ~85%).

How to use
- Call grade_and_schedule(card, user_state, rating) after the learner grades a
  flashcard (rating 0..5). It will update the DB fields on both objects and
  return (interval_days, half_life_days, p0_estimate).
"""

from dataclasses import dataclass
import math
from datetime import timedelta
from django.utils import timezone


def _sigmoid(x: float) -> float:
    """Numerically stable logistic."""
    if x > 12:
        return 0.999994
    if x < -12:
        return 0.000006
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class AISRSConfig:
    # Learning rates for online logistic update
    lr_user: float = 0.15   # learner ability theta
    lr_item: float = 0.10   # item difficulty d

    # Scheduling goal
    target_recall: float = 0.85  # aim to review when p(recall) ≈ 85%

    # Bounds and guards
    min_half_life: float = 0.5    # days
    max_half_life: float = 365.0  # days
    min_interval: int = 1         # days
    max_interval: int = 90        # days


CFG = AISRSConfig()


def grade_and_schedule(card, user_state, rating: int, now=None, cfg: AISRSConfig = CFG):
    """
    Apply one AI-SRS update step and schedule the next review.

    Params
    - card: Flashcard instance (must have fields ai_difficulty, half_life_days,
            interval_days, due_at, repetitions, lapses)
    - user_state: SRSUserState instance (must have field theta)
    - rating: int in 0..5 (0-2 incorrect/low confidence; 3 meh; 4-5 correct)
    - now: optional timezone-aware datetime (defaults to timezone.now())

    Returns
    - (interval_days, half_life_days, p0_estimate)
    """
    now = now or timezone.now()

    # Convert rating to a binary target for logistic learning
    # Treat 4/5 as "correct"; 0-3 as not strong enough
    y = 1 if rating >= 4 else 0

    theta = float(user_state.theta)          # learner ability
    diff = float(card.ai_difficulty)         # item difficulty
    h = float(card.half_life_days or 0.0)    # memory half-life (days)
    if h <= 0:
        h = cfg.min_half_life

    # Immediate mastery estimate before forgetting
    p0 = _sigmoid(theta - diff)

    # Online logistic update (like one SGD step on log-loss)
    error = y - p0
    theta = theta + cfg.lr_user * error
    diff = diff - cfg.lr_item * error

    # Update memory half-life multiplicatively
    if y == 1:
        # Stronger gains with higher rating:
        # rating=4 -> +25%, rating=5 -> +50%
        factor = 1.0 + 0.25 * max(0, rating - 3)
        h = min(cfg.max_half_life, h * factor)
    else:
        # Incorrect/low confidence halves half-life (but bounded)
        h = max(cfg.min_half_life, h * 0.5)

    # Choose next interval t so that expected recall at review time ≈ target
    # Simple forgetting curve: p(t) = 2^(-t / h)  =>  t = -h * log2(target)
    # Use natural log to avoid base issues.
    t = int(round(-h * (math.log(cfg.target_recall) / math.log(2))))
    t = max(cfg.min_interval, min(cfg.max_interval, t))
    # If current mastery is low, force a short repeat
    if p0 < 0.6:
        t = cfg.min_interval

    # Persist updates
    user_state.theta = theta
    user_state.save(update_fields=["theta", "updated_at"])

    card.ai_difficulty = diff
    card.half_life_days = h
    card.interval_days = t
    card.due_at = now + timedelta(days=t)
    if y == 1:
        card.repetitions = (card.repetitions or 0) + 1
    else:
        card.repetitions = 0
        card.lapses = (card.lapses or 0) + 1
    card.save(update_fields=[
        "ai_difficulty", "half_life_days", "interval_days", "due_at",
        "repetitions", "lapses", "updated_at"
    ])

    return t, h, p0