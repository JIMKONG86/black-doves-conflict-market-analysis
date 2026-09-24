from .actor import Actor

class Company(Actor):
    def __init__(
        self,
        actor_id,
        name,
        ticker,
        sector,
        home_country,

    ):
        super().__init__(actor_id, name)
        self.ticker = ticker
        self.sector = sector
        self.home_country = home_country
        self.price_history = []


    def add_price_observation(self, observation):
        self.price_history.append(observation)

    def generate_price_history(self):
        for observation in self.price_history:
            yield observation
