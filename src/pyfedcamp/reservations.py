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
        self.eval_cancellations()

        with importlib.resources.path('pyfedcamp.static', 'NPS_logo.png') as logo_path:
            self.logo = str(logo_path)

        if create_placards:
            self.placard_records()
            if self.placards_df.empty:
                raise ValueError(f"No records found for the specified arrival date - {self.arrival_date}. Cannot create placards.")
            
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

    def eval_cancellations(self):
        '''
        Identify cancelled sites with no other active reservations.
        These need to be further investigated to ensure that they are not active because of a
        multi-site reservation or some other reason.
        '''
        cancelled_sites = self.res_df[
            self.res_df['Reservation Status'] == 'CANCELLED'
        ]['Site #'].unique()

        active_status = ['RESERVED', 'CHECKED_IN', 'CHECKED_OUT']
        active_sites = self.res_df[
            self.res_df['Reservation Status'].isin(active_status)
        ]['Site #'].unique()

        self.potential_cancellations = list(set(cancelled_sites) - set(active_sites))

def validate_name_format(name):
    """
    Validates that the name follows the obfuscated format: 'L............, F.....'.
    Returns True if valid, False otherwise.
    """
    import re
    pattern = r"^[A-Za-z]+\.*?, [A-Za-z]\.*$"
    return bool(re.match(pattern, name))