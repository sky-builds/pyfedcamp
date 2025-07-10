import pytest
import os
from pyfedcamp.reservations import Reservations

@pytest.fixture
def sample_file():
    return os.path.join(os.path.dirname(__file__), "data", "Camping_Reservation_Detail_2025-07-08_to_2025-07-08.xlsx")

def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        Reservations("nonexistent_file.xlsx")

def test_reservations_process_spreadsheet(sample_file):
    assert os.path.exists(sample_file), "Sample data file does not exist for testing."
    res = Reservations(sample_file)
    assert hasattr(res, "location")
    assert hasattr(res, "run_date")
    assert not res.reservations.empty
    for col in [
        "Reservation #", "ReservationNumber", "SiteNumber", "Arrival Date",
        "ArrivalDate", "CheckInTag", "Departure Date", "DepartureDate",
        "Camper Footprint", "observed", "occupied", "Overnights", "Occupants", "Primary Occupant Name"
    ]:
        assert col in res.reservations.columns

def test_occupied_overnights_and_summary(sample_file):
    res = Reservations(sample_file)
    assert not res.occupied_reservations_by_day.empty
    assert not res.daily_reservation_summary.empty
    for col in ["total_sites", "total_occupants"]:
        assert col in res.daily_reservation_summary.columns

def test_busiest_day_of_week(sample_file):
    res = Reservations(sample_file)
    res.busiest_day_of_week()
    assert hasattr(res, "busiest_days")
    assert not res.busiest_days.empty
    for col in ["week", "Occupied Date", "day", "total_occupants", "weighted_occupants"]:
        assert col in res.busiest_days.columns

def test_build_download_package(sample_file, tmp_path):
    res = Reservations(sample_file)
    zip_bytes = res.build_download_package(format="zip", output_path=None)
    assert isinstance(zip_bytes, bytes)
    tar_path = tmp_path / "output.tar.gz"
    out_path = res.build_download_package(format="tar.gz", output_path=str(tar_path))
    assert os.path.exists(out_path)