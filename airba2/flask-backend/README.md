# Flask Backend Project

This project is a Flask backend application that interacts with a PostgreSQL database and supports CORS for cross-origin requests. It provides a RESTful API for frontend applications to communicate with.

## Project Structure

```
flask-backend
├── app
│   ├── __init__.py          # Initializes the Flask application, sets up CORS and PostgreSQL connection.
│   ├── config.py            # Contains application configuration settings, including database connection parameters and CORS settings.
│   ├── models
│   │   ├── __init__.py      # Initializes the models package.
│   │   └── user.py          # Defines the user model and the structure of the users table in the database.
│   ├── routes
│   │   ├── __init__.py      # Initializes the routes package.
│   │   └── api.py           # Contains RESTful API routes that handle requests to application resources.
│   └── utils
│       ├── __init__.py      # Initializes the utilities package.
│       └── helpers.py       # Contains helper functions used throughout the application.
├── instance
│   └── config.py            # Contains instance-specific configuration, such as secret keys and database parameters.
├── migrations
│   └── README.md            # Information about database migrations.
├── static
│   ├── css
│   │   └── style.css        # CSS styles (not used in backend but may be useful for frontend).
│   └── js
│       └── main.js          # JavaScript (not used in backend but may be useful for frontend).
├── templates
│   └── base.html            # Base HTML template (not used in backend but may be useful for frontend).
├── tests
│   ├── __init__.py          # Initializes the tests package.
│   ├── conftest.py          # Contains test configuration, including fixtures.
│   └── test_api.py          # Tests for API routes.
├── .env.example              # Example environment file containing environment variables.
├── .flaskenv                # Contains environment variables for Flask, such as FLASK_APP and FLASK_ENV.
├── .gitignore               # Specifies files and folders to ignore in git.
├── requirements.txt         # List of project dependencies for installation.
├── run.py                   # Entry point for running the Flask application.
└── README.md                # Documentation for the project.
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd flask-backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up the database and migrations (ensure PostgreSQL is running):
   ```
   # Follow the instructions in migrations/README.md
   ```

## Usage

To run the application, use the following command:
```
flask run
```

Make sure to set the necessary environment variables in the `.flaskenv` file or in your environment.

## API Documentation

Refer to the `app/routes/api.py` file for details on the available API endpoints and their usage.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.