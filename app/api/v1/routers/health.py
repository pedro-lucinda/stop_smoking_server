from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth0 import get_current_user
from app.api.v1.dependencies.db import get_async_db
from app.core.health import (
    calculate_breathing,
    calculate_carbon_monoxide_level,
    calculate_circulation,
    calculate_decreased_risk_of_heart_attack,
    calculate_decreased_risk_of_lung_cancer,
    calculate_energy_levels,
    calculate_gum_texture,
    calculate_immunity_and_lung_function,
    calculate_life_regained_in_hours,
    calculate_nicotine_expelled,
    calculate_oxygen_levels,
    calculate_pulse_rate,
    calculate_reduced_risk_of_heart_disease,
    calculate_taste_and_smell,
)
from app.models.preference import Preference
from app.schemas.health import HealthOut

router = APIRouter()


@router.get("/", response_model=HealthOut, status_code=status.HTTP_200_OK)
async def get_health_data(
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
) -> HealthOut:
    """
    Compute health metrics based on the user's quit_date.
    Avoid async lazy-loads by querying Preference explicitly.
    """
    # Load the user's Preference explicitly (no lazy access via current_user.preference)
    res = await db.execute(
        select(Preference).where(Preference.user_id == current_user.id)
    )
    pref = res.scalar_one_or_none()
    if not pref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found"
        )

    quit_date = pref.quit_date
    days_since_quit = (date.today() - quit_date).days

    nicotine_expelled = calculate_nicotine_expelled(days_since_quit)
    carbon_monoxide_level = calculate_carbon_monoxide_level(days_since_quit)
    pulse_rate = calculate_pulse_rate(days_since_quit)
    oxygen_levels = calculate_oxygen_levels(days_since_quit)
    taste_and_smell = calculate_taste_and_smell(days_since_quit)
    breathing = calculate_breathing(days_since_quit)
    energy_levels = calculate_energy_levels(days_since_quit)
    circulation = calculate_circulation(days_since_quit)
    gum_texture = calculate_gum_texture(days_since_quit)
    immunity_and_lung_function = calculate_immunity_and_lung_function(days_since_quit)
    reduced_risk_of_heart_disease = calculate_reduced_risk_of_heart_disease(
        days_since_quit
    )
    decreased_risk_of_lung_cancer = calculate_decreased_risk_of_lung_cancer(
        days_since_quit
    )
    decreased_risk_of_heart_attack = calculate_decreased_risk_of_heart_attack(
        days_since_quit
    )
    life_regained_in_hours = calculate_life_regained_in_hours(days_since_quit)

    return HealthOut(
        pulse_rate=pulse_rate,
        oxygen_levels=oxygen_levels,
        carbon_monoxide_level=carbon_monoxide_level,
        nicotine_expelled=nicotine_expelled,
        taste_and_smell=taste_and_smell,
        date=date.today(),
        breathing=breathing,
        energy_levels=energy_levels,
        circulation=circulation,
        gum_texture=gum_texture,
        immunity_and_lung_function=immunity_and_lung_function,
        reduced_risk_of_heart_disease=reduced_risk_of_heart_disease,
        decreased_risk_of_lung_cancer=decreased_risk_of_lung_cancer,
        decreased_risk_of_heart_attack=decreased_risk_of_heart_attack,
        life_regained_in_hours=life_regained_in_hours,
    )
