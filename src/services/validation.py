def validate_reported_count(value, field_name):
    if value is None:
        return True

    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"'{field_name}' must be an integer, got {type(value).__name__}")

    if value < 0:
        raise ValueError(f"'{field_name}' cannot be less than zero, got {value}")

    return True