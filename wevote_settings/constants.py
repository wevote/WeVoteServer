# wevote_settings/constants.py

ELECTION_YEARS_AVAILABLE = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]

# When we update IS_BATTLEGROUND_YEARS_AVAILABLE, update at the same time:
#  OfficeHeld.is_battleground_race_2019 (etc.), Politician, and Representative
IS_BATTLEGROUND_YEARS_AVAILABLE = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]

# When we update OFFICE_HELD_YEARS_AVAILABLE, update at the same time:
#  OfficeHeld.year_with_data_2023 (etc.) and Representative.year_in_office_2023 (etc.)
#  We also need to update the OFFICE_HELD_YEARS_AVAILABLE variable in WebApp
OFFICE_HELD_YEARS_AVAILABLE = [2023, 2024, 2025, 2026]
