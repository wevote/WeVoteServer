# wevote_settings/constants.py

ELECTION_YEARS_AVAILABLE = [2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016]
# When we update this list, at least two db tables need to update at the same time:
#  OfficeHeld.year_with_data_2023 (etc.) and Representative.year_in_office_2023 (etc.)
OFFICE_HELD_YEARS_AVAILABLE = [2023, 2024, 2025, 2026]
