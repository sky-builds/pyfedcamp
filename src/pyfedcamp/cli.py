import argparse
from pyfedcamp.reservations import Reservations
import sys

def main():
    parser = argparse.ArgumentParser(description="Process Recreation.gov Camping Reservation Detail Report spreadsheet.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Placards subcommand
    placards_parser = subparsers.add_parser("placards", help="Generate placards PDF")
    placards_parser.add_argument("input_file", help="Path to the Camping Reservation Detail Report spreadsheet (Excel file)")
    placards_parser.add_argument("--output_path", default=".", help="Directory for output files")
    placards_parser.add_argument("--filename", required=True, help="Filename for the generated placards PDF")
    placards_parser.add_argument("--campsites", nargs="*", default=None, help="List of specific campsites to include", type=str)
    placards_parser.add_argument("--agency", default="NPS", help="U.S. Federal agency operating the campground", type=str)
    placards_parser.add_argument("--fed_unit", default="Black Canyon of the Gunnison National Park", type=str)
    placards_parser.add_argument("--campground", default="South Rim Campground", type=str)
    placards_parser.add_argument("--camp_host_site", default="A33", type=str)

    # Reports subcommand
    report_parser = subparsers.add_parser("reports", help="Generate summary report")
    report_parser.add_argument("input_file", help="Path to the Camping Reservation Detail Report spreadsheet (Excel file)")
    report_parser.add_argument("--output_path", default=".", help="Directory for output files")
    report_parser.add_argument("--filename", required=True, help="Filename for the generated reports PDF")

    # Download package subcommand
    pkg_parser = subparsers.add_parser("download-data", help="Download transformed data as a zip or tar.gz archive")
    pkg_parser.add_argument("input_file", help="Path to the reservation spreadsheet (Excel file)")
    pkg_parser.add_argument("--format", choices=["zip", "tar.gz"], default="zip", help="Archive format")
    pkg_parser.add_argument("--output_path", default=None, help="Path with filename to save archive (if omitted, stream to stdout)")

    args = parser.parse_args()

    if args.command == "placards":
        res = Reservations(input_file=args.input_file)
        res.build_placards(
            output_path=args.output_path,
            filename=args.placards_filename,
            campsites=args.campsites,
            agency=args.agency,
            fed_unit=args.fed_unit,
            campground=args.campground,
            camp_host_site=args.camp_host_site
        )
        print(f"Placards generated and saved to {args.output_path}/{args.placards_filename}")

    elif args.command == "reports":
        res = Reservations(input_file=args.input_file)
        # Placeholder for report generation logic
        print(f"Reports generated and saved to {args.output_path}/{args.reports_filename}")

    elif args.command == "download-data":
        res = Reservations(input_file=args.input_file)
        if args.output_path:
            out_path = args.output_path
            res.build_download_package(format=args.format, output_path=out_path)
            print(f"Archive written to {out_path}")
        else:
            # Stream to stdout (for piping or web)
            data = res.build_download_package(format=args.format, output_path=None)
            sys.stdout.buffer.write(data)

if __name__ == "__main__":
    main()