from datetime import date

from pydantic import BaseModel


class HealthOut(BaseModel):
    """HealthOut schema for health-related data.
    This schema is used to represent health metrics and improvements over time.
    It includes various health indicators that can be tracked daily.
    Attributes:
      date (date): The date of the health record.
      pulse_rate (int): The user's pulse rate.
      oxygen_levels (int): The user's oxygen levels.
      carbon_monoxide_level (int): The level of carbon monoxide in the user's body.
      nicotine_expelled (int): The amount of nicotine expelled from the user's body.
      taste_and_smell (int): Improvement in taste and smell perception.
      breathing (int): Improvement in breathing function.
      energy_levels (int): Improvement in energy levels.
      circulation (int): Improvement in blood circulation.
      gum_texture (int): Improvement in gum texture.
      immunity_and_lung_function (int): Improvement in immunity and lung function.
      reduced_risk_of_heart_disease (int): Reduced risk of heart disease.
      decreased_risk_of_lung_cancer (int): Decreased risk of lung cancer.
      decreased_risk_of_heart_attack (int): Decreased risk of heart attack.
      life_regained_in_hours (int): Estimated life regained in hours.
    """

    date: date
    pulse_rate: int
    oxygen_levels: int
    carbon_monoxide_level: int
    nicotine_expelled: int
    taste_and_smell: int
    breathing: int
    energy_levels: int
    circulation: int
    gum_texture: int
    immunity_and_lung_function: int
    reduced_risk_of_heart_disease: int
    decreased_risk_of_lung_cancer: int
    decreased_risk_of_heart_attack: int
    life_regained_in_hours: int

    class Config:
        from_attributes = True
