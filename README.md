# pyFedCamp
This package works with data from the recreation.gov system for camping reservations on U.S. Federal lands. It makes up for a number of things not covered in "The Hub" (the system used for managing reservations and campground operations). In the current version of the toolset, the only input file processed is the Camping Reservation Detail Report (the one with obfuscated Personally Identifiable Information). The Reservations class validates the structure of the file by checking for the required column headings (located in the spreadsheet after some header information) and the necessary obfuscation on PII in Primary Occupant Names. If the rec.gov folks change the file structure, as they did on the equipment list in 2024, that may trigger the need for an upgrade to this package to account for the changes.

## Installation

**Requirements:**  
- Python 3.10 or higher

It's recommended to upgrade pip before installing:

```sh
python -m pip install --upgrade pip
```

Install the latest release from PyPI:

```sh
pip install pyfedcamp
```

### Install from source (for development)

Clone the repository and install in editable mode:

```sh
git clone https://github.com/yourusername/pyfedcamp.git
cd pyfedcamp
pip install -e .
```

#### With Poetry

```sh
poetry install
```

## Command Line Interface

After installing `pyfedcamp`, you can use the command line tool to generate placards or reports from your reservation spreadsheet.

### Usage

```sh
pyfedcamp <command> [options]
```

### Subcommands

#### `placards`

Generate placards PDF for check-in.

**Usage:**
```sh
pyfedcamp placards <input_file> --filename <output.pdf> [options]
```

**Options:**

| Option              | Required | Default                                   | Description                                               |
|---------------------|----------|-------------------------------------------|-----------------------------------------------------------|
| `input_file`        | Yes      | —                                         | Path to the Camping Reservation Detail Report spreadsheet |
| `--filename`        | Yes      | —                                         | Filename for the generated placards PDF                   |
| `--output_path`     | No       | `.`                                       | Directory for output files                                |
| `--campsites`       | No       | None                                      | List of specific campsites to include                     |
| `--agency`          | No       | `NPS`                                     | U.S. Federal agency operating the campground              |
| `--fed_unit`        | No       | `Black Canyon of the Gunnison National Park` | Federal unit name                                     |
| `--campground`      | No       | `South Rim Campground`                    | Campground name                                           |
| `--camp_host_site`  | No       | `A33`                                     | Camp host site number                                     |
| `--location`  | No       | None                                     | Location string used in place of fed_unit and campground                                     |

**Example:**
```sh
pyfedcamp placards ~/Downloads/Camping_Reservation_Detail.xlsx --filename placards.pdf --output_path ~/Downloads --campsites A1 A2 A3
```

---

#### `reports`

Generate summary reports from reservation data.

**Usage:**
```sh
pyfedcamp reports <input_file> --filename <output.pdf> [options]
```

**Options:**

| Option          | Required | Default | Description                                               |
|-----------------|----------|---------|-----------------------------------------------------------|
| `input_file`    | Yes      | —       | Path to the Camping Reservation Detail Report spreadsheet |
| `--filename`    | Yes      | —       | Filename for the generated reports PDF                    |
| `--output_path` | No       | `.`     | Directory for output files                                |

**Example:**
```sh
pyfedcamp reports ~/Downloads/Camping_Reservation_Detail.xlsx --filename reports.pdf --output_path ~/Downloads
```

#### `download-data`

Download all major dataframes derived from the source input Excel file as CSV files in a single archive.

**Usage:**
```sh
pyfedcamp download-data <input_file> --format zip --output_path data.zip
```

**Options:**

| Option          | Required | Default | Description                                      |
|-----------------|----------|---------|--------------------------------------------------|
| `input_file`    | Yes      | —       | Path to the reservation spreadsheet              |
| `--format`      | No       | zip     | Archive format: `zip` or `tar.gz`                |
| `--output_path` | No       | None    | Path to save archive (omit to stream to stdout)  |

**Example:**
```sh
pyfedcamp download-data Camping_Reservation_Detail_Report.xlsx --format tar.gz --output_path reservation_data.tar.gz
```

## Derived Data Structures

The `Reservations` class produces several intermediate and summary DataFrames during processing:

- **reservations**: The main DataFrame containing all reservation records loaded from the input spreadsheet, with additional columns for reporting and filtering.
- **occupied_reservations_by_day**: Expanded DataFrame with one row per occupied night per reservation, including date, occupants, and site footprint.
- **daily_reservation_summary**: Summarized reservations from occupied_reservations_by_day summing total sites, total occupants, total sites by footprint (tent or RV), and total occupants by stay duration (single-night, first-night, or continuing).
- **busiest_days**: Identification of busiest day of each week represented in the input data based on number of occupants on site (for interpretive programming planning purposes) with single-/first-night occupants weighted higher.

These DataFrames are available as attributes of the `Reservations` instance after running the relevant methods.

## Placards
The seminal use case for pyFedCamp was the production of custom placards to be printed out and placed on sign posts for each campsite on the day/night of initial reservation. NPS staff had been tweaking the existing placard print-out from rec.gov to make things larger so that members of staff, camp hosts, and guests could read them at a distance. All of the data necessary to produce the placards is contained in the Camping Reservation Detail report, including the site number, reservation number, obfuscated (non-PII) customer initials, number of occupants, arrival/departure date, and other information.

The build_placards function in the Reservations class takes a list of dictionaries containing the pertinent details for each placard in a placard_records parameter. If not provided when invoked, the list is popiulated from viable records in the currently provided input_file. Viable records have an arrival date from the current date forward and a reservation status of RESERVED. In practice, users may want to produce the list of reservations through a separate process such as selecting specific campsites.

The build_placards function uses the [Python ReportLab](https://docs.reportlab.com/) package to produce an 8.5x11 PDF with up to 4 placards per sheet, similar to the built-in rec.gov report. The placards are customized with an appropriate logo for the managing agency, name of the park/unit, name of the campground, and help details for where camp hosts or rangers can be found.

## Extensibility
pyFedCamp was written initially for use at two National Park Service units, Black Canyon of the Gunnison National Park and the Colorado National Monument. It was built from the perspective of a campground host with functionality for that role based on specific use cases and areas where the existing functionality in the rec.gov "Hub" (management portal for that system) fell short. I tried to build parameters such that it could work for other U.S. Federal campgrounds, but some additional features and resources will need to be incorporated. Custom placards, in particular, require parameters such as the park/unit name and campground name. Additional logos would be needed for other agencies. This could be handled by building in a static resource file containing the necessary details, changing the code to reference some type of identifier (e.g., BLCA is the standard NPS 4-character identifier for the Black Canyon National Park).

If there is significant interest in extending this toolset for other units and use cases, I will work on an approach. My hope would be that the rec.gov folks actually start using all the great suggestions that have come in through their "Ideas Portal" and get better functionality built into their system, hopefully obsolescing this package.

