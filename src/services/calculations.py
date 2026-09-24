def calculate_total_reported_deaths(observations):
    total = 0

    for observation in observations:
        if observation.reported_civilian_deaths is not None:
            total += observation.reported_civilian_deaths

        if observation.reported_military_deaths is not None:
            total += observation.reported_military_deaths

    return total


def calculate_total_reported_destroyed_facilities(observations):
    total = 0

    for observation in observations:
        if observation.reported_civilian_facilities_destroyed is not None:
            total += observation.reported_civilian_facilities_destroyed

        if observation.reported_military_facilities_destroyed is not None:
            total += observation.reported_military_facilities_destroyed

    return total