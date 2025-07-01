# Copyright (c) 2025 SkyBuilds, LLC
# This file is part of pyfedcamp and is licensed under the MIT License.

import pandas as pd
import os
import random
import re
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
import importlib.resources
from typing import List, Optional
from datetime import date
import calendar

class Reservations:
    def __init__(
            self, 
            input_file: str, 
            output_dir: str = '.', 
            agency: str = 'NPS',
            placards_filename: str = 'placards.pdf',
            create_placards: bool = False,
            arrival_dates: Optional[List[date]] = None,
            fed_unit: str = 'Black Canyon of the Gunnison National Park',
            campground: str = 'South Rim Campground',
            campsites: Optional[List[str]] = None
        ):
        self.input_file = input_file
        self.output_dir = output_dir
        self.placards_filename = placards_filename
        self.arrival_dates = arrival_dates if arrival_dates is not None else [date.today()]
        self.fed_unit = fed_unit
        self.campground = campground
        self.campsites = campsites if campsites is not None else []

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"The file {input_file} does not exist.")
        
        self.process_spreadsheet()
        self.get_occupied_reservations()
        self.get_occupied_overnights()

        self.site_summary()
        self.occupant_summary()
        self.build_weekly_summary()
        self.identify_busiest_days()

        with importlib.resources.path('pyfedcamp.static', f'{agency}_logo.png') as logo_path:
            self.logo = str(logo_path)

        if create_placards:
            self.placard_records()
            if self.placards_df.empty:
                raise ValueError(f"No records found for the specified arrival date(s). Cannot create placards.")
            
            self.build_placards()

    def process_spreadsheet(self):
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

        try:
            self.res_df = pd.read_excel(self.input_file, engine='openpyxl', header=None)
        except Exception as e:
            raise ValueError(f"Error reading the Excel file: {e}")

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

        header_row_index = self.res_df.apply(lambda row: all(col in row.values for col in required_columns), axis=1).idxmax()

        # Ensure we have a valid header row in the spreadsheet
        if header_row_index == 0:
            raise ValueError("No row found that contains all required columns.")

        # Rebuild the DataFrame with the correct column names
        self.res_df.columns = self.res_df.iloc[header_row_index]
        self.res_df = self.res_df[header_row_index + 1:].reset_index(drop=True)

        # Validate random sampling of "Primary Occupant Name"
        sample_size = min(10, len(self.res_df))  # Check up to 10 random rows
        sampled_names = random.sample(list(self.res_df['Primary Occupant Name']), sample_size)
        invalid_names = [name for name in sampled_names if not validate_name_format(name)]

        if invalid_names:
            raise ValueError(f"Names in the 'Primary Occupant Name' column do not appear to be obfuscated for PII. The spreadsheet cannot be processed.")

        # Set date columns to datetime format and create string representations
        date_columns = ['Arrival Date', 'Departure Date']
        for col in date_columns:
            self.res_df[col] = pd.to_datetime(self.res_df[col], errors='coerce')
            self.res_df[f"{col}_str"] = self.res_df[col].dt.strftime('%m/%d')

        # Set an Arrival Month column for statistical summaries
        self.res_df['Arrival Month'] = self.res_df['Arrival Date'].dt.month
        self.res_df['Arrival Month Text'] = self.res_df['Arrival Month'].apply(lambda m: calendar.month_name[m])
        self.res_df['Arrival Year'] = self.res_df['Arrival Date'].dt.year
        self.res_df['Arrival MonthYear'] = self.res_df['Arrival Month Text'] + ' ' + self.res_df['Arrival Year'].astype(str)
        
        # Set an obfuscated version of the Reservation Number
        self.res_df['ReservationNumber'] = self.res_df['Reservation #'].apply(lambda x: f"...{str(x)[-6:]}")

        # Split the 'Equipment' column into a list of equipment items
        self.res_df['Equipment List'] = self.res_df['Equipment'].apply(
            lambda x: [re.sub(r'\s*\(\d+\)$', '', item.strip()) for item in x.split(',')]
        )

        # Create a logical split between tent and RV reservations
        self.res_df['Camper Footprint'] = self.res_df['Equipment List'].apply(
            lambda equipment: 'tent' if all(item.lower() in ['tent', 'small tent'] for item in equipment) else 'RV'
        )

        # Use the reservation status to set a variable for reservations observed by staff
        self.res_df['observed'] = self.res_df['Reservation Status'].isin(['CHECKED_IN', 'CHECKED_OUT'])

        # Ensure "Nights/ Days" is an integer
        self.res_df['Nights/ Days'] = pd.to_numeric(self.res_df['Nights/ Days'], errors='coerce').fillna(0).astype(int)

        # Ensure # of Occupants is an integer for report generation
        self.res_df['# of Occupants'] = pd.to_numeric(self.res_df['# of Occupants'], errors='coerce').fillna(0).astype(int)

        # Calculate "occupant overnights" as Nights/ Days * # of Occupants
        self.res_df['Occupant Overnights'] = self.res_df['Nights/ Days'] * self.res_df['# of Occupants']

        # Create a column for the reporting category
        self.res_df['Reporting Category'] = self.res_df.apply(reporting_category, axis=1)

    def get_occupied_reservations(self):
        self.occupied_reservations = self.res_df[
            self.res_df['Reservation Status'].isin(
                [
                    'RESERVED',
                    'CHECKED_IN',
                    'CHECKED_OUT'
                ]
            )
        ].reset_index(drop=True)

    def get_occupied_overnights(self):
        overnight_expanded = []
        for idx, row in self.occupied_reservations.iterrows():
            # Create a unique reservation ID (customize as needed for uniqueness)
            reservation_id = row.get('Reservation #', idx)  # Use a real unique field if available
            nights = (row['Departure Date'] - row['Arrival Date']).days
            for night_num, single_date in enumerate(pd.date_range(row['Arrival Date'], row['Departure Date'] - pd.Timedelta(days=1)), start=1):
                overnight_expanded.append({
                    'date': single_date,
                    'overnight_occupants': row['Occupant Overnights'] if 'Occupant Overnights' in row else row['# of Occupants'],
                    'footprint': row['Camper Footprint'],
                    'reservation_id': reservation_id,
                    'night_number': night_num,
                    'total_nights': nights
                })

        self.occupied_overnights = pd.DataFrame(overnight_expanded)
        self.occupied_overnights['year'] = self.occupied_overnights['date'].dt.year
        self.occupied_overnights['week'] = self.occupied_overnights['date'].dt.isocalendar().week
        self.occupied_overnights['month'] = self.occupied_overnights['date'].dt.month_name()
        self.occupied_overnights['day'] = self.occupied_overnights['date'].dt.day_name()

        self.first_nights = self.occupied_overnights[
            (self.occupied_overnights['night_number'] == 1)
            & 
            (self.occupied_overnights['total_nights'] > 1)
        ]
    
        self.single_nights = self.occupied_overnights[
            (self.occupied_overnights['night_number'] == 1)
            & 
            (self.occupied_overnights['total_nights'] == 1)
        ]

    def site_summary(self):
        self.sites_per_night = (
            self.occupied_overnights.groupby(['date', 'year', 'month', 'week', 'day', 'footprint'])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )

    def occupant_summary(self):
        self.occupants_per_night = (
            self.occupied_overnights.groupby(['date', 'year', 'month', 'week', 'day', 'footprint'])['overnight_occupants']
            .sum()
            .unstack(fill_value=0)
            .reset_index()
        )

    def build_weekly_summary(self):
        # Group both single_nights and first_nights by year, week, and day of week, summing overnight_occupants
        single_night_summary = (
            self.single_nights.groupby(['year', 'week', 'day'])
            .agg({'overnight_occupants': 'sum'})
            .rename(columns={'overnight_occupants': 'single_night_occupants'})
            .reset_index()
        )

        first_night_summary = (
            self.first_nights.groupby(['year', 'week', 'day'])
            .agg({'overnight_occupants': 'sum'})
            .rename(columns={'overnight_occupants': 'first_night_occupants'})
            .reset_index()
        )

        # Merge the first/single summaries on year, week, and day
        self.weekly_occupants = pd.merge(
            single_night_summary,
            first_night_summary,
            on=['year', 'week', 'day'],
            how='outer'
        ).fillna(0)

        # Build in a sum of total occupants
        total_occupants_summary = (
            self.occupied_overnights.groupby(['year', 'week', 'day'])
            .agg({'overnight_occupants': 'sum'})
            .rename(columns={'overnight_occupants': 'total_occupants'})
            .reset_index()
        )

        # Merge total_occupants into weekly_occupants
        self.weekly_occupants = pd.merge(
            self.weekly_occupants,
            total_occupants_summary,
            on=['year', 'week', 'day'],
            how='outer'
        ).fillna(0)

        # Convert occupant counts to integers
        self.weekly_occupants['single_night_occupants'] = self.weekly_occupants['single_night_occupants'].astype(int)
        self.weekly_occupants['first_night_occupants'] = self.weekly_occupants['first_night_occupants'].astype(int)
        self.weekly_occupants['total_occupants'] = self.weekly_occupants['total_occupants'].astype(int)

        # Add first_single_night_occupants column
        self.weekly_occupants['first_single_night_occupants'] = (
            self.weekly_occupants['single_night_occupants'] + self.weekly_occupants['first_night_occupants']
        )

        # Sort for readability
        self.weekly_occupants.sort_values(['year', 'week', 'day'], inplace=True)

    def identify_busiest_days(self, weight=2):
        # Compute a weighted score
        self.weekly_occupants['weighted_occupants'] = (
            self.weekly_occupants['total_occupants'] + 
            weight * self.weekly_occupants['first_single_night_occupants']
        )

        # Find the day with the highest weighted occupants for each week
        idx = self.weekly_occupants.groupby('week')['weighted_occupants'].idxmax()
        self.busiest_days = self.weekly_occupants.loc[idx, ['week', 'day', 'total_occupants', 'first_single_night_occupants', 'weighted_occupants']]

        self.busiest_days.reset_index(drop=True, inplace=True)

    def placard_records(self):
        mask = (
            (self.res_df['Reservation Status'] == 'RESERVED')
            &
            (self.res_df['Arrival Date'].dt.date.isin(self.arrival_dates))
        )
        # If campsites list is not empty, filter for those sites as well
        if self.campsites:
            mask = mask & (self.res_df['Site #'].isin(self.campsites))
        self.placards_df = self.res_df[mask].copy()

    def build_placards(self):
        # Set canvas size to 8.5x11 inches in landscape orientation (792x612 points)
        canvas_width = 792
        canvas_height = 612
        placard_width = canvas_width / 2  # Half the width
        placard_height = canvas_height / 2  # Half the height

        margin_width = 15
        logo_width = 54
        logo_height = 69

        info_box_y = 30
        info_box_height = 100
        info_box_width = placard_width / 3

       # Ensure output directory exists and create canvas to output path
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, self.placards_filename)
        c = canvas.Canvas(output_path, pagesize=landscape((canvas_width, canvas_height)))

        quadrant_positions = [
            (0, canvas_height / 2),  # Top-left
            (canvas_width / 2, canvas_height / 2),  # Top-right
            (0, 0),  # Bottom-left
            (canvas_width / 2, 0)  # Bottom-right
        ]

        for i, row in enumerate(self.placards_df.iterrows()):
            # Determine the quadrant for the current placard
            quadrant_index = i % 4
            x_offset, y_offset = quadrant_positions[quadrant_index]

            # Draw the rectangle for the placard
            c.rect(x_offset, y_offset, placard_width, placard_height, stroke=1, fill=0)

            # Draw the logo
            c.drawImage(self.logo, x=x_offset + margin_width, y=y_offset + placard_height - logo_height - margin_width - 30, width=logo_width, height=logo_height)

            # Add text content
            title_box = c.beginText()
            title_box.setTextOrigin(x_offset + margin_width + logo_width + 10, y_offset + placard_height - 60)
            title_box.setFont("Helvetica", 12)
            title_box.textLine(self.fed_unit)
            title_box.textLine(self.campground)
            title_box.textLine("")
            title_box.setFont("Helvetica-Bold", 18)
            title_box.textLine("RESERVED SITE")
            c.drawText(title_box)

            site_text = f"Site: {row[1]['Site #']}"
            site_text_width = c.stringWidth(site_text, "Helvetica-Bold", 14)
            site_text_pos = x_offset + placard_width - site_text_width - margin_width
            c.setFont("Helvetica-Bold", 14)
            c.drawString(site_text_pos, y_offset + placard_height - 110, site_text)

            visitor_box = c.beginText()
            visitor_box.setTextOrigin(x_offset + margin_width, y_offset + placard_height - 140)
            visitor_box.setFont("Helvetica", 10)
            visitor_box.textLine("Visitor:")
            visitor_box.textLine("")
            visitor_box.setFont("Helvetica-Bold", 14)
            visitor_box.textLine(row[1]['Primary Occupant Name'])
            visitor_box.textLine("")
            visitor_box.setFont("Helvetica", 10)
            visitor_box.textLine(f"Reservation#: {row[1]['ReservationNumber']}")
            c.drawText(visitor_box)

            arrival_box = c.beginText()
            arrival_box.setTextOrigin(x_offset + placard_width / 2 - 50, y_offset + placard_height - 140)
            arrival_box.setFont("Helvetica", 10)
            arrival_box.textLine("Arrival:")
            arrival_box.textLine("")
            arrival_box.textLine("")
            arrival_box.setFont("Helvetica-Bold", 30)
            arrival_box.textLine(row[1]['Arrival Date_str'])
            c.drawText(arrival_box)

            departure_box = c.beginText()
            departure_box.setTextOrigin(x_offset + placard_width / 2 + 70, y_offset + placard_height - 140)
            departure_box.setFont("Helvetica", 10)
            departure_box.textLine("Departure:")
            departure_box.textLine("")
            departure_box.textLine("")
            departure_box.setFont("Helvetica-Bold", 15)
            departure_box.textLine(f"{str(row[1]['Departure Date_str']).split('/')[0]}/")
            departure_box.textLine("")
            departure_box.setFont("Helvetica-Bold", 80)
            departure_box.textLine(f" {str(row[1]['Departure Date_str']).split('/')[-1]}")
            c.drawText(departure_box)

            help_box = c.beginText()
            help_box.setTextOrigin(x_offset + margin_width, y_offset + margin_width + 40)
            help_box.setFont("Helvetica", 8)
            help_box.textLine("For immediate assistance: contact camp host in site A33")
            help_box.textLine("For reservations: www.recreation.gov or call 1-877-444-6777")
            c.drawText(help_box)

            for j in range(3):
                info_box_x = x_offset + j * info_box_width
                c.rect(info_box_x, y_offset + info_box_y + 50, info_box_width, info_box_height, stroke=1, fill=0)

            # Start a new page after every 4 placards
            if quadrant_index == 3:
                c.showPage()

        # Save the canvas
        c.save()


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