# Car Rental System

Welcome to the Car Rental System project! This repository contains the source code for a web-based car rental system that allows users to rent cars and car owners to list their vehicles for rent. The system includes an admin login for managing the platform.

## Features

- User registration and login
- Car owner registration and login
- Admin login and dashboard
- Car listing and management by car owners
- Car booking and rental by users
- Booking cancellation process with admin confirmation

## Technologies Used

- Frontend: HTML, CSS, JavaScript
- Backend: Flask (Python)
- Database: SQLite
- Authentication: Flask-Login
- Templates: Jinja2

## Usage

### Register as a user or car owner:

- Users can register and log in to browse and book cars.
- Car owners can register and log in to list their cars for rent.

### Admin login:

- Admin can log in to manage the platform, including user and car owner management, and handle booking cancellations.

### Book a car:

- Users can browse available cars, view details, and book cars for specific dates.

### Manage car listings:

- Car owners can add, edit, and delete car listings through their dashboard.

### Cancellation process:

- Admin can send cancellation requests to clients for approved bookings. Upon confirmation, the booking status will change to "Cancellation Request Sent".
