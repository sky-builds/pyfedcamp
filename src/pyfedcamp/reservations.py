# Copyright (c) 2025 SkyBuilds, LLC
# This file is part of pyfedcamp and is licensed under the MIT License.

import pandas as pd
import os
import random
import re
from datetime import date, datetime
import io
import zipfile
import tarfile
import tempfile
import re
import dateutil.parser

class Reservations:
    def __init__(
            self, 
            input_file: str
        ):
        self.input_file = input_file

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"The file {input_file} does not exist.")
        
        self.process_spreadsheet()
        self.get_occupied_overnights()
        self.summarize_reservations()
        self.busiest_day_of_week()

    def process_spreadsheet(self):
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

        try:
            df = pd.read_excel(self.input_file, engine='openpyxl', header=None)
        except Exception as e:
            raise ValueError(f"Error reading the Excel file: {e}")

        # --- Extract Location and Run Date/Time from the first few rows ---
        self.location = None
        self.run_date = None
        for i in range(min(10, len(df))):
            row = df.iloc[i].astype(str)
            first_cell = row.iloc[0]
            if first_cell.startswith("Location:"):
                self.location = first_cell.replace("Location:", "").strip()
            elif first_cell.startswith("Run Date and Time:"):
                # e.g., "Run Date and Time: Jul 07, 2025, 08:08:00 US/Mountain"
                match = re.search(r"Run Date and Time:\s*(.+)", first_cell)
                if match:
                    date_str = match.group(1)
                    date_str_parts = date_str.rsplit(' ', 1)
                    if len(date_str_parts) == 2:
                        self.run_date = datetime.strptime(date_str_parts[0], '%b %d, %Y, %H:%M:%S')
                        self.run_date_tz = date_str_parts[1]
                    else:
                        self.run_date = date_str

        required_columns = [
            'Loop',
            'Site #',
            'Reservation #', 
            'Reservation Status',
            'Arrival Date', 
            'Departure Date',
            'Primary Occupant Name',
            '# of Occupants',
            'Equipment',
            'Nights/ Days',
        ]

        header_row_index = df.apply(lambda row: all(col in row.values for col in required_columns), axis=1).idxmax()

        # Ensure we have a valid header row in the spreadsheet
        if header_row_index == 0:
            raise ValueError("No row found that contains all required columns.")

        # Rebuild the DataFrame with the correct column names
        df.columns = df.iloc[header_row_index]
        df = df[header_row_index + 1:].reset_index(drop=True)

        # Set a variable for the original data
        self.original_data = df.copy()

        # Validate random sampling of "Primary Occupant Name"
        sample_size = min(10, len(df))  # Check up to 10 random rows
        sampled_names = random.sample(list(df['Primary Occupant Name']), sample_size)
        invalid_names = [name for name in sampled_names if not validate_name_format(name)]

        if invalid_names:
            raise ValueError(f"Names in the 'Primary Occupant Name' column do not appear to be obfuscated for PII. The spreadsheet cannot be processed.")

        # Rename the site # field
        df.rename(columns={'Site #': 'SiteNumber'}, inplace=True)

        # Set date columns to datetime format and create string representations
        for col in ['Arrival Date', 'Departure Date']:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df[col.replace(" ", "")] = df[col].dt.strftime('%m/%d')

        # Set the CheckInTag value based on current/future arrival dates and reservation status
        today = pd.to_datetime(datetime.today().date())
        df['CheckInTag'] = df.apply(lambda row: (row['Arrival Date'] >= today) and (row['Reservation Status'] == 'RESERVED'), axis=1)

        # Set an obfuscated version of the Reservation Number
        df['ReservationNumber'] = df['Reservation #'].apply(lambda x: f"...{str(x)[-6:]}")

        # Split the 'Equipment' column into a list of equipment items, handle empty/missing values
        df['Equipment List'] = df['Equipment'].apply(
            lambda x: [re.sub(r'\s*\(\d+\)$', '', item.strip()) for item in x.split(',')] if pd.notnull(x) and str(x).strip() else []
        )

        # Set Camper Footprint: 'tent', 'RV', or 'unknown' if equipment list is empty
        df['Camper Footprint'] = df['Equipment List'].apply(
            lambda equipment: (
                'tent' if any(item.lower() in ['tent', 'small tent'] for item in equipment)
                else 'RV' if equipment else 'unknown'
            )
        )

        # Use the reservation status to set variables for reservations observed by staff and (presumably) occupied by guests
        df['observed'] = df['Reservation Status'].isin(['CHECKED_IN', 'CHECKED_OUT'])
        df['occupied'] = df['Reservation Status'].isin(['CHECKED_IN', 'CHECKED_OUT', 'RESERVED'])

        # Ensure "Nights/ Days" is an integer
        df['Overnights'] = pd.to_numeric(df['Nights/ Days'], errors='coerce').fillna(0).astype(int)

        # Ensure # of Occupants is an integer for report generation
        df['Occupants'] = pd.to_numeric(df['# of Occupants'], errors='coerce').fillna(0).astype(int)

        # Set the resulting dataframe and serializable JSON structure
        core_attributes = [
            'Reservation #',
            'ReservationNumber',
            'SiteNumber',
            'Arrival Date',
            'ArrivalDate',
            'CheckInTag',
            'Departure Date',
            'DepartureDate',
            'Camper Footprint',
            'observed',
            'occupied',
            'Overnights',
            'Occupants',
            'Primary Occupant Name'
        ]
        self.reservations = df[core_attributes].copy()

    def get_occupied_overnights(self):
        # Expand reservations into individual nights with Reservation Footprint
        expanded_rows = []
        for idx, row in self.reservations[self.reservations['occupied']].iterrows():
            arrival = row['Arrival Date']
            departure = row['Departure Date']
            nights = (departure - arrival).days
            for i, single_date in enumerate(pd.date_range(arrival, departure - pd.Timedelta(days=1))):
                if nights == 1:
                    footprint = "single night"
                elif i == 0:
                    footprint = "first night"
                else:
                    footprint = "continuing night"
                expanded_row = row.copy()
                expanded_row['Occupied Date'] = single_date
                expanded_row['Duration'] = footprint
                expanded_rows.append(expanded_row)

        occupied_reservation_dates = pd.DataFrame(expanded_rows)
        occupied_reservation_dates = occupied_reservation_dates[[
            'Occupied Date',
            'SiteNumber',
            'Camper Footprint',
            'Occupants',
            'Duration'
        ]]

        self.occupied_reservations_by_day = occupied_reservation_dates.copy()

    def summarize_reservations(self):
        # 1. Total sites and total occupants per day
        summary_stats = self.occupied_reservations_by_day.groupby('Occupied Date').agg(
            total_sites=('SiteNumber', 'nunique'),
            total_occupants=('Occupants', 'sum')
        ).reset_index()

        # 2. RV and tent sites per day
        footprint_sites = self.occupied_reservations_by_day.groupby(['Occupied Date', 'Camper Footprint'])['SiteNumber'].nunique().unstack(fill_value=0)
        footprint_sites = footprint_sites.rename(columns={'RV': 'rv_sites', 'tent': 'tent_sites'}).reset_index()

        # 3. Occupants by duration per day
        duration_occupants = self.occupied_reservations_by_day.pivot_table(
            index='Occupied Date',
            columns='Duration',
            values='Occupants',
            aggfunc='sum',
            fill_value=0
        ).rename(columns={
            'first night': 'first_night_occupants',
            'single night': 'single_night_occupants',
            'continuing night': 'continuing_night_occupants'
        }).reset_index()

        # 4. Merge all together
        summary_stats = summary_stats.merge(footprint_sites, on='Occupied Date', how='left')
        summary_stats = summary_stats.merge(duration_occupants, on='Occupied Date', how='left')

        summary_stats['year'] = summary_stats['Occupied Date'].dt.year
        summary_stats['month'] = summary_stats['Occupied Date'].dt.strftime('%B')
        summary_stats['week'] = summary_stats['Occupied Date'].dt.isocalendar().week
        summary_stats['day'] = summary_stats['Occupied Date'].dt.strftime('%A')

        self.daily_reservation_summary = summary_stats

    def busiest_day_of_week(
            self,
            WEIGHT_FIRST: int = 3,
            WEIGHT_SINGLE: int = 2,
            WEIGHT_CONTINUING: int = 1
        ):
        # 1. Calculate weighted occupants
        df = self.daily_reservation_summary.copy()
        df['weighted_occupants'] = (
            WEIGHT_FIRST * df.get('first_night_occupants', 0) +
            WEIGHT_SINGLE * df.get('single_night_occupants', 0) +
            WEIGHT_CONTINUING * df.get('continuing_night_occupants', 0)
        )

        # 2. Identify the busiest day in each week
        busiest_idx = df.groupby('week')['weighted_occupants'].idxmax()
        busiest_days = df.loc[busiest_idx, ['week', 'Occupied Date', 'day', 'total_occupants', 'first_night_occupants', 'single_night_occupants', 'continuing_night_occupants', 'weighted_occupants']]
        self.busiest_days = busiest_days.sort_values('week').reset_index(drop=True)

    def build_download_package(
        self,
        format: str = "zip",
        output_path: str = "."
    ):
        """
        Package major DataFrames as CSV files into a zip or tar.gz archive.
        If output_path is None, returns bytes; else writes to output_path.
        """
        # DataFrames to include
        dfs = {
            "reservations.csv": self.reservations,
            "occupied_reservations_by_day.csv": self.occupied_reservations_by_day,
            "daily_reservation_summary.csv": self.daily_reservation_summary,
        }
        if hasattr(self, "busiest_days"):
            dfs["busiest_days.csv"] = self.busiest_days

        # Use a temp directory for CSVs
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_paths = []
            for fname, df in dfs.items():
                csv_path = os.path.join(tmpdir, fname)
                df.to_csv(csv_path, index=False)
                csv_paths.append((fname, csv_path))

            # Prepare archive in memory or on disk
            if output_path is None:
                buffer = io.BytesIO()
                if format == "zip":
                    with zipfile.ZipFile(buffer, "w") as zf:
                        for fname, path in csv_paths:
                            zf.write(path, arcname=fname)
                elif format in ("tar", "tgz", "tar.gz"):
                    mode = "w:gz" if format in ("tgz", "tar.gz") else "w"
                    with tarfile.open(fileobj=buffer, mode=mode) as tf:
                        for fname, path in csv_paths:
                            tf.add(path, arcname=fname)
                else:
                    raise ValueError("Unsupported format. Use 'zip' or 'tar.gz'.")
                buffer.seek(0)
                return buffer.getvalue()
            else:
                if format == "zip":
                    with zipfile.ZipFile(output_path, "w") as zf:
                        for fname, path in csv_paths:
                            zf.write(path, arcname=fname)
                elif format in ("tar", "tgz", "tar.gz"):
                    mode = "w:gz" if format in ("tgz", "tar.gz") else "w"
                    with tarfile.open(output_path, mode=mode) as tf:
                        for fname, path in csv_paths:
                            tf.add(path, arcname=fname)
                else:
                    raise ValueError("Unsupported format. Use 'zip' or 'tar.gz'.")
                return output_path

def validate_name_format(name):
    """
    Validates that the name follows the obfuscated format: 'L............, F.....'.
    Returns True if valid, False otherwise.
    """
    import re
    pattern = r"^[A-Za-z]+\.*?, [A-Za-z]\.*$"
    return bool(re.match(pattern, name))

def reporting_category(row):
    if row['Reservation Status'] in ['RESERVED', 'CHECKED_IN', 'CHECKED_OUT']:
        cat = row['Arrival MonthYear'] + ' - ' + row['Camper Footprint']
        if row['observed']:
            cat += ' - Observed'
        else:
            cat += ' - Not Observed'
        return cat
    else:
        return None
    