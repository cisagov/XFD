"""Stakeholder model for the WAS application."""

# Standard Python Libraries
from string import printable

# Third-Party Libraries
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

# ============================================================
# Password character constraints
# ============================================================

BANNED_CHARACTERS = ["'"]
PASSWORD_CHARACTER_SET = printable.strip()
for character in BANNED_CHARACTERS:
    PASSWORD_CHARACTER_SET = PASSWORD_CHARACTER_SET.replace(character, "")

# TODO: Consider moving to SSM or environment variable for flexibility.
PASSWORD_LENGTH = 24


def validate_report_password(value: str):
    """Ensure the report_password contains only allowed characters."""
    for ch in value:
        if ch not in PASSWORD_CHARACTER_SET:
            raise ValidationError(
                f"Character '{ch}' is not allowed in report_password."
            )


# ============================================================
# ENUMS
# ============================================================


class USStates(models.TextChoices):
    """States and territories of the United States, including DC and territories."""

    BLANK = "", ""
    AK = "AK", "AK"
    AL = "AL", "AL"
    AR = "AR", "AR"
    AZ = "AZ", "AZ"
    CA = "CA", "CA"
    CO = "CO", "CO"
    CT = "CT", "CT"
    DE = "DE", "DE"
    FL = "FL", "FL"
    GA = "GA", "GA"
    HI = "HI", "HI"
    IA = "IA", "IA"
    ID = "ID", "ID"
    IL = "IL", "IL"
    IN = "IN", "IN"
    KS = "KS", "KS"
    KY = "KY", "KY"
    LA = "LA", "LA"
    MA = "MA", "MA"
    MD = "MD", "MD"
    ME = "ME", "ME"
    MI = "MI", "MI"
    MN = "MN", "MN"
    MO = "MO", "MO"
    MS = "MS", "MS"
    MT = "MT", "MT"
    NC = "NC", "NC"
    ND = "ND", "ND"
    NE = "NE", "NE"
    NH = "NH", "NH"
    NJ = "NJ", "NJ"
    NM = "NM", "NM"
    NV = "NV", "NV"
    NY = "NY", "NY"
    OH = "OH", "OH"
    OK = "OK", "OK"
    OR = "OR", "OR"
    PA = "PA", "PA"
    RI = "RI", "RI"
    SC = "SC", "SC"
    SD = "SD", "SD"
    TN = "TN", "TN"
    TX = "TX", "TX"
    UT = "UT", "UT"
    VA = "VA", "VA"
    VT = "VT", "VT"
    WA = "WA", "WA"
    WI = "WI", "WI"
    WV = "WV", "WV"
    WY = "WY", "WY"
    DC = "DC", "DC"
    AS = "AS", "AS"
    GU = "GU", "GU"
    MP = "MP", "MP"
    PR = "PR", "PR"
    VI = "VI", "VI"


class TestingSectorChoices(models.TextChoices):
    """Testing sector choices for the WAS application."""

    FEDERAL = "Federal Government Entity"
    STATE = "State Government Entity"
    LOCAL = "Local Government Entity"
    TRIBAL = "Tribal Government Entity"
    TERRITORIAL = "Territorial Government Entity"
    PRIVATE = "Private Sector Entity"
    OTHER = "Other"


class CITypeChoices(models.TextChoices):
    """Critical Infrastructure (CI) type choices for the WAS application."""

    BLANK = "", ""
    CI_CHEMICAL = "CI_CHEMICAL"
    CI_COMMERCIAL_FACILITIES = "CI_COMMERCIAL_FACILITIES"
    CI_COMMUNICATIONS = "CI_COMMUNICATIONS"
    CI_CRITICAL_MANUFACTURING = "CI_CRITICAL_MANUFACTURING"
    CI_DAMS = "CI_DAMS"
    CI_DEFENSE_INDUSTRIAL_BASE = "CI_DEFENSE_INDUSTRIAL_BASE"
    CI_EMERGENCY_SERVICES = "CI_EMERGENCY_SERVICES"
    CI_ENERGY = "CI_ENERGY"
    CI_FINANCIAL_SERVICES = "CI_FINANCIAL_SERVICES"
    CI_FOOD_AND_AGRICULTURE = "CI_FOOD_AND_AGRICULTURE"
    CI_GOVERNMENT_FACILITIES = "CI_GOVERNMENT_FACILITIES"
    CI_HEALTHCARE_AND_PUBLIC_HEALTH = "CI_HEALTHCARE_AND_PUBLIC_HEALTH"
    CI_INFORMATION_TECHNOLOGY = "CI_INFORMATION_TECHNOLOGY"
    CI_NUCLEAR_REACTORS = "CI_NUCLEAR_REACTORS_MATERIALS_AND_WASTE"
    CI_TRANSPORTATION_SYSTEMS = "CI_TRANSPORTATION_SYSTEMS"
    CI_WATER_AND_WASTEWATER_SYSTEMS = "CI_WATER_AND_WASTEWATER_SYSTEMS"


class SubtypeChoices(models.TextChoices):
    """Subtype choices for the WAS application."""

    BLANK = "", ""
    EDUCATION = "EDUCATION"
    HOSPITALITY = "HOSPITALITY"
    LEGAL = "LEGAL SERVICES"
    NONPROFIT = "NON-PROFIT"
    SPORTS = "SPORTS ORGANIZATIONS"


class FrequencyChoices(models.TextChoices):
    """Frequency choices for the WAS application."""

    MONTHLY = "Monthly"
    BIWEEKLY = "Bi-weekly"
    QUARTERLY = "Quarterly"
    ANNUALLY = "Annually"
    OTHER = "Other"


# ============================================================
# Stakeholder MODEL
# ============================================================


class Stakeholder(models.Model):
    """Stakeholder model for the WAS application."""

    tag = models.CharField(max_length=128, primary_key=True)

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    parent_tag = models.CharField(max_length=128, blank=True)

    customer_name = models.CharField(max_length=512)
    comments = models.TextField(blank=True)

    ci_type = models.CharField(
        max_length=128, choices=CITypeChoices.choices, default=CITypeChoices.BLANK
    )

    testing_sector = models.CharField(
        max_length=256,
        choices=TestingSectorChoices.choices,
        default=TestingSectorChoices.OTHER,
    )

    subtype = models.CharField(
        max_length=128, choices=SubtypeChoices.choices, default=SubtypeChoices.BLANK
    )

    frequency = models.CharField(
        max_length=64,
        choices=FrequencyChoices.choices,
        default=FrequencyChoices.MONTHLY,
    )

    ticket = models.CharField(max_length=128, blank=True)
    distro_email = models.TextField(blank=True)
    tech_poc_email = models.TextField(blank=True)
    was_report_poc = models.TextField(blank=True)

    num_web_apps = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    web_apps_last_updated = models.BigIntegerField(null=True, blank=True)
    last_scanned = models.BigIntegerField(null=True, blank=True)
    next_scheduled = models.BigIntegerField(null=True, blank=True)
    onboarding_date = models.BigIntegerField(null=True, blank=True)

    elections = models.BooleanField(default=False)
    fceb = models.BooleanField(default=False)
    manual_report = models.BooleanField(default=False)
    retired = models.BooleanField(default=False)

    state = models.CharField(
        max_length=64, choices=USStates.choices, default=USStates.BLANK
    )

    report_password = models.CharField(
        max_length=256,
        blank=True,
        validators=[validate_report_password],
        help_text="Password must not contain banned characters.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for the Stakeholder model."""

        db_table = "WAS_Stakeholder"

    def __str__(self):
        """Return a string representation of the Stakeholder instance."""
        return f"{self.tag} — {self.customer_name}"

    def clean(self):
        """Clean the stakeholder instance."""
        # Auto-sync parent_tag with parent FK
        if self.parent:
            self.parent_tag = self.parent.tag
        else:
            self.parent_tag = ""
