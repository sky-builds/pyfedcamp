# pyFedCamp
This package works with data from the recreation.gov system for camping reservations on U.S. Federal lands. It makes up for a number of things not covered in "The Hub" (the system used for managing reservations and campground operations).

## Input Parameters
The following are required input parameters for the Reservations class:

* input_file (str) - The relative or absolute path to the Camping Reservation Detail Report input file that will be processed
* create_placards (bool) - True to run the build_placards function and generate the downloadable PDF file
* placards_filename (str) - Defaults to 'placards.pdf'
* fed_unit (str) - The display name for the U.S. Federal land unit that will be examined and processed
* campground (str) - The display name for the specific campground on the Federal land unit
* arrival_dates (list of dates) - One or more arrival dates (date objects) that must be found in the input file for placards; defaults to today's date
* campsites (list of strings) - Optional list of campsites to filter on from the input data when only certain sites need to be printed or reported on

## Generated DataFrames

The `Reservations` class produces several intermediate and summary DataFrames during processing:

- **res_df**: The main DataFrame containing all reservation records loaded from the input spreadsheet, with additional columns for reporting and filtering.
- **occupied_reservations**: Filtered reservations that are currently reserved, checked in, or checked out.
- **occupied_overnights**: Expanded DataFrame with one row per occupied night per reservation, including date, occupants, and site footprint.
- **first_nights**: Subset of `occupied_overnights` for the first night of multi-night reservations.
- **single_nights**: Subset of `occupied_overnights` for single-night reservations.
- **sites_per_night**: Summary of the number of occupied sites per night, grouped by date and site type.
- **occupants_per_night**: Summary of the number of occupants per night, grouped by date and site type.
- **weekly_occupants**: Weekly summary of occupants, including single-night, first-night, and total occupants, grouped by year, week, and day.
- **busiest_days**: For each week, the day with the highest weighted occupancy.
- **placards_df**: Filtered DataFrame containing only the reservations for which placards will be generated.

These DataFrames are available as attributes of the `Reservations` instance after running the relevant methods.

## Placards
The seminal use case for pyFedCamp was the production of custom placards to be printed out and placed on sign posts for each campsite on the day/night of initial reservation. We found ourselves tweaking the existing placard print-out from rec.gov to make things larger so that members of staff and guests could read them at a distance. All of the data necessary to produce the placards is contained in the Camping Reservation Detail report, including the obfuscated (non-PII) customer initials, arrival/departure date, and other information.

The Reservations class handles reading the Excel file produced in the Camping Reservation Detail Report, ensuring that the file is in the expected format (more on this in the dependencies section), and builds a dataframe from the actual data part of the worksheet (minus multiple header rows). The build_placards function uses the [Python ReportLab](https://docs.reportlab.com/) package to produce an 8.5x11 PDF with up to 4 placards per sheet, similar to the built-in rec.gov report.

