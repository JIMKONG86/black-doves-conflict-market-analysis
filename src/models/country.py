from .actor import Actor

class Country(Actor):
    def __init__(self, actor_id, name, iso_code):
        super().__init__(actor_id, name)
        self.iso_code = iso_code
        self.role_history = []

    def add_role_observation(self, observation):
        self.role_history.append(observation)

    def generate_role_history(self):
        for observation in self.role_history:
            yield observation
