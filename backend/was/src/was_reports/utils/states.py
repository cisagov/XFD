"""Validation helpers for stakeholder state and territory codes."""

US_STATE_AND_TERRITORY_CODES = frozenset(
    {
        "AK",
        "AL",
        "AR",
        "AS",
        "AZ",
        "CA",
        "CO",
        "CT",
        "DC",
        "DE",
        "FL",
        "GA",
        "GU",
        "HI",
        "IA",
        "ID",
        "IL",
        "IN",
        "KS",
        "KY",
        "LA",
        "MA",
        "MD",
        "ME",
        "MI",
        "MN",
        "MO",
        "MP",
        "MS",
        "MT",
        "NC",
        "ND",
        "NE",
        "NH",
        "NJ",
        "NM",
        "NV",
        "NY",
        "OH",
        "OK",
        "OR",
        "PA",
        "PR",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VA",
        "VI",
        "VT",
        "WA",
        "WI",
        "WV",
        "WY",
    }
)


def validate_state_code(value: str) -> str:
    """Require an exact uppercase USPS state or territory abbreviation."""
    normalized_value = value.strip()
    if normalized_value != value or normalized_value != normalized_value.upper():
        raise ValueError(
            "State must be an uppercase two-letter state or territory code."
        )
    if normalized_value not in US_STATE_AND_TERRITORY_CODES:
        raise ValueError(
            "State must be a valid uppercase two-letter state or territory code."
        )
    return normalized_value
