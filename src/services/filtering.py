def generate_observations_by_status(observations, required_status):
    for observation in observations:
        if observation.verification_status == required_status:
            yield observation
