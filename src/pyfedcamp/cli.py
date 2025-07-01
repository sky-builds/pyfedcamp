import argparse
from pyfedcamp.reservations import Reservations

def main():
    parser = argparse.ArgumentParser(description="Process Recreation.gov Camping Reservation Detail Report spreadsheet.")
    parser.add_argument("input_file", help="Path to the reservation spreadsheet (Excel file)")
    parser.add_argument("--output-dir", default=".", help="Directory for output files")
    parser.add_argument("--placards", action="store_true", help="Generate placards PDF")
    parser.add_argument("--arrival-date", nargs="*", help="Arrival date(s) for placards (YYYY-MM-DD)", type=str)
    parser.add_argument("--campsites", nargs="*", help="List of specific campsites to include in producing check-in placards", type=str)
    args = parser.parse_args()

    arrival_dates = None
    if args.arrival_date:
        from datetime import datetime
        arrival_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in args.arrival_date]

    Reservations(
        input_file=args.input_file,
        output_dir=args.output_dir,
        create_placards=args.placards,
        arrival_dates=arrival_dates,
        campsites=args.campsites
    )

if __name__ == "__main__":
    main()