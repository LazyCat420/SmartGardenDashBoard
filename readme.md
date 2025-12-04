# 🌱 Smart Garden Dashboard

A modern, AI-powered garden management dashboard that uses natural language processing to automatically extract and categorize your garden data from simple notes.

![Smart Garden Dashboard](https://img.shields.io/badge/Python-3.8+-green.svg)
![LMStudio](https://img.shields.io/badge/LLM-LMStudio-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### 🤖 AI-Powered Note Processing
Simply type natural language notes like:
> "Today I planted 5 tomato seedlings in the raised bed. Watered all my basil plants. The peppers look great, about 20cm tall now. Need to add fertilizer next week."

The AI will automatically extract and categorize:
- 🌱 New plant entries
- 💧 Watering logs
- 🧪 Fertilization records
- 📏 Growth measurements
- 🥕 Harvest data
- 🐛 Pest issues
- ✅ Tasks and reminders
- 🌤️ Weather conditions

### 📊 Comprehensive Dashboard
- **Plant Management**: Track all your plants with variety, location, planting dates
- **Growth Tracking**: Log height, width, leaf count, and health ratings over time
- **Task System**: Create and manage garden tasks with priorities and recurring schedules
- **Harvest Log**: Record all your harvests with quantities and quality ratings
- **Weather Tracking**: Log weather conditions to correlate with plant health
- **Visual Charts**: See plant health at a glance with interactive charts

### 🎨 Modern UI
- Beautiful dark theme optimized for any lighting
- Responsive design works on desktop and mobile
- Intuitive navigation with emoji icons
- Real-time status indicators

## 🚀 Quick Start

### Prerequisites
1. **Python 3.8+** - [Download Python](https://python.org)
2. **LMStudio** - [Download LMStudio](https://lmstudio.ai/) (for AI features)

### One-Click Installation

1. Clone or download this repository
2. **Double-click `install.bat`** - This will:
   - Create a virtual environment
   - Install all dependencies
   - Initialize the database

3. **Set up LMStudio** (for AI features):
   - Open LMStudio
   - Download a model (recommended: `granite-3.3-8b-instruct` or similar)
   - Go to "Local Server" tab
   - Start the server on port 1234

4. **Double-click `run.bat`** to start the application

5. Open your browser to **http://localhost:5000**

## 📖 Usage Guide

### Adding Data with AI Notes

The easiest way to add data is through natural language notes:

1. Go to the Dashboard
2. Type your garden observations in the "Quick Note" box
3. Click "Process with AI"
4. Review the extracted actions
5. Click "Apply All Actions" to save

**Example Notes:**
```
Planted cherry tomatoes and basil in the greenhouse today.
```
```
Watered everything this morning. The tomatoes are 30cm tall and looking healthy.
Noticed some aphids on the pepper plants - sprayed with neem oil.
```
```
Harvested 2kg of zucchini! Quality is excellent.
Need to fertilize the tomatoes tomorrow.
```

### Manual Data Entry

You can also add data manually:
- **Plants**: Click "+ Add Plant" on the Plants page
- **Tasks**: Click "+ Add Task" on the Tasks page
- **Weather**: Click "+ Log Weather" on the Weather page
- **Growth/Watering**: Use the buttons on each plant card

## 🏗️ Project Structure

```
SmartGardenDashBoard/
├── backend/
│   ├── main.py          # Flask app with all API endpoints
│   ├── llm_service.py   # LLM integration service
│   └── garden.db        # SQLite database (created on first run)
├── frontend/
│   ├── index.html       # Main HTML file
│   ├── styles.css       # CSS styles
│   └── app.js           # Frontend JavaScript
├── install.bat          # One-click installer
├── run.bat              # Application launcher
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🔧 API Endpoints

### Plants
- `GET /api/plants` - List all plants
- `POST /api/plants` - Add a new plant
- `GET /api/plants/<id>` - Get plant details
- `PUT /api/plants/<id>` - Update plant
- `DELETE /api/plants/<id>` - Delete plant

### Growth Logs
- `GET /api/plants/<id>/growth` - Get growth history
- `POST /api/plants/<id>/growth` - Add growth log

### Tasks
- `GET /api/tasks` - List tasks
- `POST /api/tasks` - Create task
- `PUT /api/tasks/<id>/complete` - Complete task
- `DELETE /api/tasks/<id>` - Delete task

### LLM
- `GET /api/llm/status` - Check LLM connection
- `POST /api/llm/process-note` - Process natural language note
- `POST /api/llm/apply-actions` - Apply extracted actions

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics

## 🧠 LLM Tool Calling

The application uses LLM tool calling to extract structured data. Available tools:

| Tool | Description |
|------|-------------|
| `add_plant` | Add a new plant to the garden |
| `log_watering` | Log a watering event |
| `log_fertilization` | Log fertilization |
| `log_harvest` | Log a harvest |
| `log_growth` | Log growth measurements |
| `report_pest_issue` | Report pest/disease |
| `create_task` | Create a garden task |
| `log_weather` | Log weather conditions |
| `update_plant_status` | Update plant status |

## 🎯 Data Categories

### Plants
- Name, variety, location
- Planting date, expected harvest
- Status (active, harvested, removed)
- Notes and images

### Growth Logs
- Height, width, leaf count
- Health rating (1-10)
- Date and notes

### Tasks
- Title, description, type
- Priority (low, medium, high)
- Due date, recurring option

### Harvests
- Plant, quantity, unit
- Quality rating
- Date and notes

### Weather
- High/low temperature
- Humidity, rainfall
- Conditions (sunny, cloudy, etc.)

## 🔒 Privacy

All data is stored locally in a SQLite database. The only external connection is to your local LMStudio server (localhost:1234). No data is sent to external servers.

## 🐛 Troubleshooting

### AI features not working
- Make sure LMStudio is running
- Check that the local server is on port 1234
- Verify a model is loaded in LMStudio

### Can't start the application
- Run `install.bat` first
- Make sure Python is in your PATH
- Check the terminal for error messages

### Database errors
- Delete `backend/garden.db` and run `install.bat` again

## 📝 License

MIT License - feel free to use and modify!

## 🙏 Acknowledgments

- [LMStudio](https://lmstudio.ai/) for local LLM inference
- [Chart.js](https://chartjs.org/) for beautiful charts
- [Flask](https://flask.palletsprojects.com/) for the backend framework
