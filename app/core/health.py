"""
Calculates recovery indices (0–100) for various health metrics
based on days since smoking cessation.
"""

import math


def _assert_non_negative(days_since_quit: int) -> int:
    if days_since_quit < 0:
        return 0
    return days_since_quit


def calculate_nicotine_expelled(days_since_quit: int) -> int:
    """
    Returns a recovery index for nicotine elimination based on days since quitting.
    Source: Benowitz et al. (2009), Handbook of Experimental Pharmacology (Elimination half-life ≈2 h) :contentReference[oaicite:12]{index=12}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    # half-life = 2 hours → tau = half_life / ln(2)
    tau_days = (2 / math.log(2)) / 24
    index = 100 * (1 - math.exp(-days_since_quit / tau_days))
    return round(min(index, 100))


def calculate_carbon_monoxide_level(days_since_quit: int) -> int:
    """
    Returns a recovery index for blood CO levels based on days since quitting.
    Source: Hanley ME. StatPearls (2023), Carboxyhemoglobin half-life ~4–6 h :contentReference[oaicite:13]{index=13}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    tau_days = (5 * 60) / math.log(2) / 1440  # 5 h avg
    index = 100 * (1 - math.exp(-days_since_quit / tau_days))
    return round(min(index, 100))


def calculate_pulse_rate(days_since_quit: int) -> int:
    """
    Returns a recovery index for pulse rate based on days since quitting.
    Source: Persico AM et al. (1992), Psychopharmacology; 9 bpm drop by day 1 :contentReference[oaicite:14]{index=14}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    return round(min(days_since_quit / 1 * 100, 100))


def calculate_oxygen_levels(days_since_quit: int) -> int:
    """
    Returns a recovery index for blood oxygen levels based on days since quitting.
    Source: U.S. Surgeon General (2020), benefits normalizing within 1–3 days :contentReference[oaicite:15]{index=15}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    return round(min(days_since_quit / 3 * 100, 100))


def calculate_taste_and_smell(days_since_quit: int) -> int:
    """
    Returns a recovery index for taste and smell based on days since quitting.
    Source: Da Ré S et al. (2017), J Comp Physiol A—sensitivity recovers by ~60 days :contentReference[oaicite:16]{index=16}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    return round(min(days_since_quit / 60 * 100, 100))


def calculate_breathing(days_since_quit: int) -> int:
    """
    Returns a recovery index for pulmonary function based on days since quitting.
    Source: U.S. Surgeon General (2020), lung function improves by 3 months :contentReference[oaicite:17]{index=17}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    return round(min(days_since_quit / 90 * 100, 100))


def calculate_energy_levels(days_since_quit: int) -> int:
    """
    Returns a recovery index for energy levels based on days since quitting.
    Source: Bao et al. (2024), Nicotine withdrawal and exercise performance improve by 3 months :contentReference[oaicite:18]{index=18}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    return round(min(days_since_quit / 90 * 100, 100))


def calculate_circulation(days_since_quit: int) -> int:
    """
    Returns a recovery index for peripheral circulation based on days since quitting.
    Source: U.S. Surgeon General (2020), circulation improves by 3 months :contentReference[oaicite:19]{index=19}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    return round(min(days_since_quit / 90 * 100, 100))


def calculate_gum_texture(days_since_quit: int) -> int:
    """
    Returns a recovery index for gum health based on days since quitting.
    Source: Duarte PM et al. (2021), J Clin Periodontol—periodontal health improves by 6 months :contentReference[oaicite:20]{index=20}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    return round(min(days_since_quit / 180 * 100, 100))


def calculate_immunity_and_lung_function(days_since_quit: int) -> int:
    """
    Returns a recovery index for immune and lung defense based on days since quitting.
    Source: Darabseh A et al. (2021), Clin Exp Immunol—markers normalize within 14 days :contentReference[oaicite:21]{index=21}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    return round(min(days_since_quit / 14 * 100, 100))


def calculate_reduced_risk_of_heart_disease(days_since_quit: int) -> int:
    """
    Returns a recovery index for coronary heart disease risk based on days since quitting.
    Source: U.S. Surgeon General (2020), risk halved by ~12 months :contentReference[oaicite:22]{index=22}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    # Exponential decay: half-life = 12 months
    t_months = days_since_quit / 30
    rr_inf = 0.5
    tau = 12 / math.log(2)
    rr_t = (1 - rr_inf) * math.exp(-t_months / tau) + rr_inf
    index = (1 - rr_t) / (1 - rr_inf) * 100
    return round(min(index, 100))


def calculate_decreased_risk_of_lung_cancer(days_since_quit: int) -> int:
    """
    Returns a recovery index for lung cancer risk based on days since quitting.
    Source: Peto R et al. (2000), Int J Epidemiol; exponential model rr∞=0.03, τ=162 months :contentReference[oaicite:23]{index=23}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    t_months = days_since_quit / 30
    rr_inf = 0.03
    tau = 162
    rr_t = (1 - rr_inf) * math.exp(-t_months / tau) + rr_inf
    index = (1 - rr_t) / (1 - rr_inf) * 100
    return round(min(index, 100))


def calculate_decreased_risk_of_heart_attack(days_since_quit: int) -> int:
    """
    Returns a recovery index for acute MI risk based on days since quitting.
    Source: U.S. Surgeon General (2020), MI risk halves by ~12 months :contentReference[oaicite:24]{index=24}
    """
    return calculate_reduced_risk_of_heart_disease(days_since_quit)


def calculate_life_regained_in_hours(days_since_quit: int) -> int:
    """
    Returns the estimated life expectancy regained (in hours) based on days since quitting smoking,
    assuming an average of 10 cigarettes/day and ~20 minutes of life lost per cigarette.

    Sources:
    - Department of Health & Social Care/UCL (2024): every cigarette costs ~20 min of life :contentReference[oaicite:17]{index=17}
    - People.com (2025): typical consumption ~10 cigarettes/day → ~200 min regained/day :contentReference[oaicite:18]{index=18}
    """
    has_not_started = _assert_non_negative(days_since_quit)
    if has_not_started == 0:
        return 0
    minutes_per_cigarette = 20
    cigarettes_per_day = 10
    hours_per_day_regained = (cigarettes_per_day * minutes_per_cigarette) / 60
    total_hours = days_since_quit * hours_per_day_regained
    return round(total_hours)
