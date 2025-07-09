# Bylaw AI Evaluation System Documentation

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [User Interface](#user-interface)
- [Setup and Installation](#setup-and-installation)
- [Usage Guide](#usage-guide)
- [Administration](#administration)
- [Troubleshooting](#troubleshooting)

## Overview

The Bylaw AI Evaluation System is a comprehensive platform for evaluating AI-generated responses to bylaw-related questions. The system supports Subject Matter Expert (SME) evaluations with a structured rubric, progress tracking, and administrative oversight.

### Key Features
- **SME Evaluation Interface**: User-friendly interface for evaluating AI responses
- **Structured Rubric**: 5-point scale evaluation across multiple criteria
- **Progress Tracking**: Visual progress indicators and completion status
- **Bookmarking System**: Save questions for later review
- **Administrative Dashboard**: Comprehensive overview and management tools
- **Data Export**: CSV export functionality for analysis
- **User Management**: Add, delete, and manage evaluators

## System Architecture

### Backend Components
- **Flask Application**: Main web server (`main.py`)
- **SQLAlchemy ORM**: Database management and models
- **SQLite Database**: Local data storage (`bylaw_eval.db`)
- **ChromaDB Integration**: Vector search for bylaw retrieval

### Frontend Components
- **Evaluation Interface**: HTML/CSS/JS for SME evaluations (`eval.html`, `eval.css`, `eval.js`)
- **Admin Dashboard**: Administrative interface (`admin.html`, `admin.css`, `admin.js`)
- **Responsive Design**: Mobile-friendly layouts

### Data Flow
1. **Question Loading**: Golden questions loaded from `eval_questions.json`
2. **AI Response Generation**: Questions sent to Gemini API via `/api/ask`
3. **Evaluation Collection**: SMEs evaluate responses using structured rubric
4. **Data Storage**: Evaluations stored in SQLite database
5. **Administrative Review**: Admin dashboard provides insights and management

## Database Schema

### Core Tables

#### Evaluation
Stores individual evaluation records submitted by SMEs.

```sql
CREATE TABLE evaluation (
    id INTEGER PRIMARY KEY,
    question TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    reference_answer TEXT,
    evaluator VARCHAR(50) NOT NULL,
    response_generated BOOLEAN NOT NULL,
    accuracy INTEGER,
    hallucination INTEGER,
    completeness INTEGER,
    authoritative INTEGER,
    usefulness INTEGER,
    comments TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    pass_fail VARCHAR(10)
);
```

#### Evaluator
Stores registered evaluator information.

```sql
CREATE TABLE evaluator (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);
```

#### EvalStatus
Tracks bookmark and skip status for each evaluator-question combination.

```sql
CREATE TABLE eval_status (
    id INTEGER PRIMARY KEY,
    evaluator VARCHAR(50) NOT NULL,
    question_idx INTEGER NOT NULL,
    bookmarked BOOLEAN DEFAULT FALSE,
    skipped BOOLEAN DEFAULT FALSE,
    UNIQUE(evaluator, question_idx)
);
```

## API Endpoints

### Evaluation Management

#### `POST /api/eval`
Submit a new evaluation.

**Request Body:**
```json
{
    "question": "What are the parking restrictions?",
    "ai_response": "According to bylaw 123...",
    "reference_answer": "",
    "evaluator": "John Doe",
    "response_generated": true,
    "accuracy": 4,
    "hallucination": 2,
    "completeness": 5,
    "authoritative": 4,
    "usefulness": 4,
    "comments": "Good response overall",
    "pass_fail": "Pass"
}
```

**Response:**
```json
{
    "status": "success"
}
```

#### `DELETE /api/eval/<eval_id>`
Delete a specific evaluation by ID.

**Response:**
```json
{
    "status": "success",
    "message": "Evaluation 123 deleted"
}
```

### Evaluator Management

#### `GET /api/evaluators`
Get list of all evaluators.

**Response:**
```json
["John Doe", "Jane Smith", "Bob Johnson"]
```

#### `POST /api/evaluators`
Add a new evaluator.

**Request Body:**
```json
{
    "name": "New Evaluator"
}
```

**Response:**
```json
{
    "status": "added",
    "name": "New Evaluator"
}
```

#### `DELETE /api/evaluators/<name>`
Delete an evaluator with options.

**Request Body:**
```json
{
    "delete_evals": false
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Evaluator John Doe deleted"
}
```

### Evaluation Status

#### `GET /api/eval-status?evaluator=<name>`
Get bookmark and skip status for an evaluator.

**Response:**
```json
[
    {
        "question_idx": 0,
        "bookmarked": true,
        "skipped": false
    }
]
```

#### `POST /api/eval-status`
Set bookmark or skip status for a question.

**Request Body:**
```json
{
    "evaluator": "John Doe",
    "question_idx": 0,
    "bookmarked": true,
    "skipped": false
}
```

### Administrative Endpoints

#### `GET /api/eval-admin/all`
Get all evaluations grouped by question and AI response.

**Response:**
```json
[
    {
        "question": "What are the parking restrictions?",
        "ai_response": "According to bylaw 123...",
        "count": 3,
        "avg_accuracy": 4.0,
        "avg_hallucination": 2.0,
        "avg_completeness": 4.5,
        "avg_authoritative": 4.0,
        "avg_usefulness": 4.0,
        "evaluations": [
            {
                "id": 123,
                "evaluator": "John Doe",
                "accuracy": 4,
                "hallucination": 2,
                "completeness": 5,
                "authoritative": 4,
                "usefulness": 4,
                "pass_fail": "Pass",
                "comments": "Good response",
                "timestamp": "2024-01-15T10:30:00"
            }
        ]
    }
]
```

#### `GET /api/eval-admin/progress`
Get progress statistics for all evaluators.

**Response:**
```json
[
    {
        "evaluator": "John Doe",
        "completed": 15,
        "total": 20,
        "avg_accuracy": 4.2,
        "avg_hallucination": 2.1,
        "avg_completeness": 4.3,
        "avg_authoritative": 4.1,
        "avg_usefulness": 4.0
    }
]
```

#### `GET /api/eval-admin/export`
Export all evaluations as CSV file.

#### `GET /api/golden-questions`
Get the list of evaluation questions.

## User Interface

### SME Evaluation Interface (`/eval`)

#### Features
- **Welcome Screen**: User selection or registration
- **Question Navigation**: Left sidebar with completion status
- **AI Response Display**: Formatted response with bylaw references
- **Evaluation Form**: Structured rubric with validation
- **Progress Tracking**: Visual completion indicators
- **Bookmarking**: Save questions for later review
- **Skip Functionality**: Mark questions as skipped

#### Evaluation Rubric
- **Response Generated**: Yes/No toggle
- **Accuracy** (1-5): How accurate is the information?
- **Hallucination** (1-5): How much false information is present? (Lower is better)
- **Completeness** (1-5): How complete is the response?
- **Authoritative** (1-5): How authoritative are the sources?
- **Usefulness** (1-5): How useful is the response overall?
- **Pass/Fail**: Overall assessment
- **Comments**: Additional feedback

#### Navigation Features
- **Left Panel**: Question list with status indicators
  - ✔️ Completed questions
  - 🔖 Bookmarked questions
  - ⏭️ Skipped questions
- **Previous/Next**: Navigate between questions
- **Bookmark/Skip**: Quick actions for question management

### Administrative Dashboard (`/admin`)

#### Features
- **SME Progress Overview**: Visual progress bars and statistics
- **Evaluation Data Table**: Comprehensive view of all evaluations
- **Filtering and Search**: Find specific evaluations
- **Expandable Rows**: View individual evaluations
- **Data Export**: CSV export for analysis
- **Delete Functionality**: Remove evaluations or users

#### Management Tools
- **User Deletion**: Delete evaluators with options
  - Delete user only (keep evaluations)
  - Delete user and all evaluations
- **Evaluation Deletion**: Remove individual evaluations
- **Progress Monitoring**: Track completion rates and scores

## Setup and Installation

### Prerequisites
- Python 3.8+
- Flask
- SQLAlchemy
- ChromaDB (for bylaw retrieval)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Stouffville-By-laws-AI
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database**
   ```bash
   cd backend
   python main.py
   ```

4. **Initialize evaluation data** (optional)
   ```bash
   flask init-eval-data
   ```

5. **Start the application**
   ```bash
   python main.py
   ```

### Configuration

#### Environment Variables
Create a `.env` file in the backend directory:

```env
GOOGLE_API_KEY=your_gemini_api_key
FLASK_ENV=development
```

#### Database Configuration
The system uses SQLite by default. Database file: `backend/bylaw_eval.db`

## Usage Guide

### For SMEs (Evaluators)

#### Getting Started
1. Navigate to `/eval` in your browser
2. Select your name from the dropdown or enter a new name
3. Click "Proceed" to start evaluating

#### Evaluating Responses
1. **Read the Question**: Understand what is being asked
2. **Review AI Response**: Read the generated response carefully
3. **Check Bylaw References**: Click on bylaw numbers to view source material
4. **Complete the Rubric**: Rate each criterion on a 1-5 scale
5. **Add Comments**: Provide additional feedback if needed
6. **Submit Evaluation**: Click "Submit Evaluation"

#### Navigation Tips
- Use the left panel to jump to specific questions
- Bookmark questions you want to review later
- Skip questions that are unclear or inappropriate
- Use Previous/Next buttons for sequential navigation

#### Validation Rules
- All rubric fields are required when "Response Generated" is "Yes"
- Pass/Fail selection is mandatory for generated responses
- Comments are optional but encouraged

### For Administrators

#### Accessing the Dashboard
1. Navigate to `/admin` in your browser
2. View overall progress and statistics

#### Monitoring Progress
- **SME Progress Section**: Visual overview of completion rates
- **Evaluation Table**: Detailed view of all evaluations
- **Filtering**: Use search and SME filter to find specific data

#### Managing Data
- **Export Data**: Use CSV export buttons for analysis
- **Delete Evaluations**: Remove individual evaluations as needed
- **Delete Users**: Remove evaluators with options for data retention

#### Best Practices
- Regularly export data for backup
- Review evaluations for quality control
- Monitor completion rates to identify issues
- Use filtering to focus on specific areas

## Administration

### User Management

#### Adding Evaluators
- Evaluators can self-register through the evaluation interface
- Administrators can also add evaluators programmatically

#### Deleting Evaluators
Two options available:
1. **User Only**: Removes the evaluator but keeps their evaluations
2. **User + Evaluations**: Removes the evaluator and all their data

#### Monitoring User Activity
- Track completion rates per evaluator
- Monitor average scores and consistency
- Identify inactive or problematic evaluators

### Data Management

#### Exporting Data
- **Cumulative Export**: Aggregated scores by question
- **Individual Export**: All individual evaluations
- **Progress Export**: User completion statistics

#### Data Cleanup
- Remove duplicate or invalid evaluations
- Clean up test data
- Archive completed evaluation sets

### Quality Control

#### Evaluation Review
- Monitor for consistent scoring patterns
- Identify potential bias or issues
- Review comments for insights

#### System Monitoring
- Track API usage and performance
- Monitor database size and growth
- Check for system errors or issues

## Troubleshooting

### Common Issues

#### Database Issues
**Problem**: Database not found or corrupted
**Solution**: 
```bash
cd backend
rm bylaw_eval.db
python main.py
```

#### API Key Issues
**Problem**: Gemini API errors
**Solution**: Check `.env` file and API key validity

#### Frontend Issues
**Problem**: JavaScript errors or broken interface
**Solution**: Clear browser cache and reload page

#### Performance Issues
**Problem**: Slow loading or timeouts
**Solution**: 
- Check database size
- Optimize queries
- Consider database indexing

### Error Messages

#### "Evaluator not found"
- User may have been deleted
- Check evaluator name spelling
- Verify user exists in database

#### "Evaluation not found"
- Evaluation may have been deleted
- Check evaluation ID validity
- Verify database integrity

#### "Missing required fields"
- Ensure all rubric fields are completed
- Check validation rules
- Verify form submission

### Debugging

#### Enable Debug Mode
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python main.py
```

#### Database Inspection
```bash
sqlite3 backend/bylaw_eval.db
.tables
SELECT * FROM evaluation LIMIT 5;
```

#### Log Analysis
Check application logs for errors:
```bash
tail -f backend/app.log
```

### Performance Optimization

#### Database Optimization
- Regular database maintenance
- Index creation for frequent queries
- Data archiving for old evaluations

#### Frontend Optimization
- Minify CSS and JavaScript
- Optimize images and assets
- Implement caching strategies

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Standards
- Follow PEP 8 for Python code
- Use meaningful variable names
- Add comments for complex logic
- Include error handling

### Testing
- Test all API endpoints
- Verify frontend functionality
- Check database operations
- Validate data integrity

---

## Version History

### v1.0.0 (Current)
- Initial evaluation system implementation
- SME evaluation interface
- Administrative dashboard
- Database schema and API endpoints
- Export functionality
- User management features

### Planned Features
- Advanced analytics and reporting
- Multi-language support
- Enhanced security features
- Integration with external systems
- Mobile application

---

*Last updated: January 2024* 