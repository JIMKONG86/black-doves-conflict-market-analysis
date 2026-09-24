from src.services.validation import (
    validate_reported_count,
)

class Observation:
    def __init__(
        self,
        observation_date,
        source,
        verification_status
    ):
        self.observation_date = observation_date
        self.source = source
        self.verification_status = verification_status
#-----------------------------------------------------------------------------

class RoleObservation(Observation):
    def __init__(
        self,
        observation_date,
        role,
        action,
        target_country,
        source,
        verification_status
    ):
        super().__init__(
            observation_date,
            source,
            verification_status
        )

        self.role = role
        self.action = action
        self.target_country = target_country

#---------------------------------------------------------------------------------

class PriceObservation(Observation):
    def __init__(
        self,
        observation_date,
        closing_price,
        currency,
        trading_volume,
        source,
        verification_status
    ):
        super().__init__(
            observation_date,
            source,
            verification_status
        )

        self.closing_price = closing_price
        self.currency = currency
        self.trading_volume = trading_volume

#--------------------------------------------------------------------------------------

class ImpactObservation(Observation):
    def __init__(
            self,
            observation_date,
            affected_country,
            reported_civilian_deaths,
            reported_military_deaths,
            reported_civilian_facilities_destroyed,
            reported_military_facilities_destroyed,
            source,
            verification_status,
     ):
            super().__init__(
                        observation_date,
                        source,
                        verification_status
                        )

            validate_reported_count(
                        reported_civilian_deaths,
                        "reported_civilian_deaths")

            validate_reported_count(
                        reported_military_deaths,
                        "reported_military_deaths",
                        )

            validate_reported_count(
                        reported_civilian_facilities_destroyed,
                        "reported_civilian_facilities_destroyed",
                        )

            validate_reported_count(
                        reported_military_facilities_destroyed,
                        "reported_military_facilities_destroyed",
                        )


            self.affected_country = affected_country
            self.reported_civilian_deaths = reported_civilian_deaths
            self.reported_military_deaths = reported_military_deaths
            self.reported_civilian_facilities_destroyed = reported_civilian_facilities_destroyed
            self.reported_military_facilities_destroyed = reported_military_facilities_destroyed

#--------------------------------------------------------------------------------------------
