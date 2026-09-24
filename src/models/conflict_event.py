from .observations import Observation

class ConflictEvent(Observation):
    def __init__(
        self,
        event_id,
        observation_date,
        description,
        initiator_country,
        target_country,
        event_type,


        source,
        verification_status
    ):
        super().__init__(
            observation_date,
            source,
            verification_status
        )

        self.event_id = event_id
        self.description = description
        self.initiator_country = initiator_country
        self.target_country = target_country
        self.event_type = event_type
        self.impact_history = []


    def add_impact_observation(self, observation):
        self.impact_history.append(observation)

    def generate_impact_history(self):
        for observation in self.impact_history:
            yield observation
