# NEET Counseling Predictor

A dynamic application to predict college options for NEET counseling based on rank, state, quota, and category.

## Features

- Dynamic form that adapts based on state selection
- Support for multiple counseling rounds
- Optimized data processing using pandas
- FastAPI backend with Streamlit frontend

## File Structure

The project contains:
- 27 Excel files with NEET counseling data for different states
- FastAPI backend (`app.py`)
- Streamlit frontend (`streamlit_app.py`)
- Combined run script (`run.py`)

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Initialize the system (analyzes all Excel files):
   ```
   python init.py
   ```

3. Run the application (starts both backend and frontend):
   ```
   python run.py
   ```

4. Access the application:
   - Backend API: http://localhost:8000/docs
   - Frontend: http://localhost:8501

## Usage

1. Select your state from the dropdown menu
2. Choose your quota (All India, State, Management, etc.)
3. Select your category (UR, SC, ST, OBC, etc.)
4. Choose the counseling round
5. Enter your NEET rank
6. Click "Find Colleges" to see which colleges you might get based on historical cutoff data

## API Endpoints

The backend provides the following API endpoints:

- `GET /states` - List all available states
- `GET /state/{state}/metadata` - Get metadata for a specific state
- `GET /state/{state}/quotas` - Get available quotas for a state
- `GET /state/{state}/categories` - Get available categories for a state
- `GET /state/{state}/rounds` - Get available rounds for a state
- `POST /query` - Query colleges based on parameters
- `POST /refresh-metadata` - Force refresh of file metadata

## Development

### Adding New Data

If you add new Excel files to the `cleaned-data 2` directory, run:
```
python init.py
```

Or use the API endpoint:
```
POST /refresh-metadata
```

### Modifying the Frontend

The Streamlit frontend is in `streamlit_app.py`. Make changes and they will be reflected when you refresh the page.

### Customizing the API

The FastAPI backend is in `app.py`. After making changes, restart the application. 