import argparse
from pyfedcamp.reservations import Reservations

def main():
    parser = argparse.ArgumentParser(description="Process Recreation.gov Camping Reservation Detail Report spreadsheet.")
    parser.add_argument("input_file", help="Path to the reservation spreadsheet (Excel file)")
    parser.add_argument("--output_path", default=".", help="Directory for output files")
    parser.add_argument("--placards_filename", default="placards.pdf", help="Filename for the generated placards PDF")
    parser.add_argument("--campsites", nargs="*", help="List of specific campsites to include in producing check-in placards", type=str)
    args = parser.parse_args()

    res = Reservations(
        input_file=args.input_file,
    )

    if args.placards_filename:
        res.build_placards(
            output_path=args.output_path,
            filename=args.placards_filename,
            campsites=args.campsites if args.campsites else None,
        )
        print(f"Placards generated and saved to {args.output_path}/{args.placards_filename}")        

if __name__ == "__main__":
    main()