# dadjoke-hotline
A demo of using openapi and vonage to make a dad joke hotline

## Running the Application

### Prerequisites
- Python 3.x
- Required packages (install with `pip install -r requirements.txt`)

### Development
To run the application in development mode:
```bash
python manage.py runserver
```

### Production with Gunicorn
To run the application with Gunicorn (recommended for production):

#### Option 1: Using the start script
```bash
./start.sh
```

#### Option 2: Direct Gunicorn command
```bash
gunicorn --config gunicorn_config.py dadjoke_hotline.wsgi:application
```

#### Option 3: Simple Gunicorn command
```bash
gunicorn --workers=2 dadjoke_hotline.wsgi:application
```

The application will be available at `http://127.0.0.1:8000`

### Configuration
- The Gunicorn configuration is in `gunicorn_config.py`
- Environment variables needed: `VONAGE_API_KEY`, `VONAGE_API_SECRET`
- The application uses SQLite database by default
