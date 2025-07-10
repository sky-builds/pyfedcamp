import io
import os
from datetime import datetime
from typing import List, Optional
from reportlab.lib.pagesizes import landscape
from reportlab.pdfgen import canvas
import importlib.resources

def build_placards(
        placard_records: List[dict],
        filename: Optional[str] = None, 
        output_path: str = '.',
        agency: str = 'NPS',
        fed_unit: str = 'Black Canyon of the Gunnison National Park',
        campground: str = 'South Rim Campground',
        camp_host_site: str = 'A33',
        location: Optional[str] = None
    ):
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

    with importlib.resources.path('pyfedcamp.static', f'{agency}_logo.png') as logo_path:
        logo = str(logo_path)

    if filename is None:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape((canvas_width, canvas_height)))
    else:
        os.makedirs(output_path, exist_ok=True)
        file_output = os.path.join(output_path, filename)
        c = canvas.Canvas(file_output, pagesize=landscape((canvas_width, canvas_height)))

    quadrant_positions = [
        (0, canvas_height / 2),  # Top-left
        (canvas_width / 2, canvas_height / 2),  # Top-right
        (0, 0),  # Bottom-left
        (canvas_width / 2, 0)  # Bottom-right
    ]

    for i, reservation in enumerate(placard_records):
        # Determine the quadrant for the current placard
        quadrant_index = i % 4
        x_offset, y_offset = quadrant_positions[quadrant_index]

        # Draw the rectangle for the placard
        c.rect(x_offset, y_offset, placard_width, placard_height, stroke=1, fill=0)

        # Draw the logo
        c.drawImage(logo, x=x_offset + margin_width, y=y_offset + placard_height - logo_height - margin_width - 30, width=logo_width, height=logo_height)

        # Add text content
        title_box = c.beginText()
        title_box.setTextOrigin(x_offset + margin_width + logo_width + 10, y_offset + placard_height - 60)
        title_box.setFont("Helvetica", 12)
        if location:
            title_box.textLine(location)
        else:
            title_box.textLine(fed_unit)
            title_box.textLine(campground)
        title_box.textLine("")
        title_box.setFont("Helvetica-Bold", 18)
        title_box.textLine("RESERVED SITE")
        c.drawText(title_box)

        site_text = f"Site: {reservation['SiteNumber']}"
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
        visitor_box.textLine(reservation['Primary Occupant Name'])
        visitor_box.textLine("")
        visitor_box.setFont("Helvetica", 10)
        visitor_box.textLine(f"Reservation#: {reservation['ReservationNumber']}")
        visitor_box.textLine(f"Occupants: {reservation['Occupants']}")
        c.drawText(visitor_box)

        arrival_box = c.beginText()
        arrival_box.setTextOrigin(x_offset + placard_width / 2 - 50, y_offset + placard_height - 140)
        arrival_box.setFont("Helvetica", 10)
        arrival_box.textLine("Arrival:")
        arrival_box.textLine("")
        arrival_box.textLine("")
        arrival_box.setFont("Helvetica-Bold", 30)
        arrival_box.textLine(reservation['ArrivalDate'])
        c.drawText(arrival_box)

        departure_box = c.beginText()
        departure_box.setTextOrigin(x_offset + placard_width / 2 + 70, y_offset + placard_height - 140)
        departure_box.setFont("Helvetica", 10)
        departure_box.textLine("Departure:")
        departure_box.textLine("")
        departure_box.textLine("")
        departure_box.setFont("Helvetica-Bold", 15)
        departure_box.textLine(f"{str(reservation['DepartureDate']).split('/')[0]}/")
        departure_box.textLine("")
        departure_box.setFont("Helvetica-Bold", 80)
        departure_box.textLine(f" {str(reservation['DepartureDate']).split('/')[-1]}")
        c.drawText(departure_box)

        help_box = c.beginText()
        help_box.setTextOrigin(x_offset + margin_width, y_offset + margin_width + 40)
        help_box.setFont("Helvetica", 8)
        if camp_host_site:
            help_box.textLine(f"For immediate assistance: contact camp host in site {camp_host_site}")
        help_box.textLine("For reservations: www.recreation.gov or call 1-877-444-6777")
        help_box.textLine("Placard printed: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        c.drawText(help_box)

        for j in range(3):
            info_box_x = x_offset + j * info_box_width
            c.rect(info_box_x, y_offset + info_box_y + 50, info_box_width, info_box_height, stroke=1, fill=0)

        # Start a new page after every 4 placards
        if quadrant_index == 3:
            c.showPage()

    # Save the canvas
    c.save()

    # If no filename is provided, return the PDF as a byte string
    if filename is None:
        buffer.seek(0)
        return buffer.getvalue()