# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.2] - 2025-06-07
### Added
- Function to evaluate cancellations, identifying potentially cancelled sites for further investigation. Reservations class yields potential_cancellations list.
- Ensured that the # of Occupants field from the Camping Reservation Detail Report data is an integer for report generation.
- Added an Arrival Month Text field containing the textual name of the arrival month for reporting purposes.

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.0.1] - 2025-06-06
### Added
- Initial release of `pyfedcamp`.
- [`Reservations`](src/pyfedcamp/reservations.py) class for processing Recreation.gov Camping Reservation Detail Reports.
- Placard PDF generation using ReportLab, with support for custom filtering by arrival date and campsite.
- Obfuscated PII validation for primary occupant names.
- Support for custom federal unit and campground names.
- Bundled static assets (e.g., NPS logo).

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

---

For earlier changes, see project history in version control.