import pytest
import os
from pyfedcamp.placards import build_placards
from pyfedcamp.reservations import Reservations

@pytest.fixture
def sample_file():
    return os.path.join(os.path.dirname(__file__), "data", "Camping_Reservation_Detail_2025-07-08_to_2025-07-08.xlsx")

def test_placards_build_placards(sample_file):
    res = Reservations(sample_file)
    test_records = res.reservations.head(4)[
        [
            'ReservationNumber',
            'SiteNumber',
            'ArrivalDate',
            'DepartureDate',
            'Primary Occupant Name',
            'Occupants'
        ]
    ].to_dict(orient='records')
    pdf_bytes = build_placards(test_records, filename=None)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 100  # Should not be empty
    assert pdf_bytes.startswith(b'%PDF')  # PDF files start with '%PDF'