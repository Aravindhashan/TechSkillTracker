# Tech Skills BI Dashboard

## Overview

This repository contains a comprehensive Streamlit-based Business Intelligence dashboard that provides advanced analytics for the tech job market. The application automatically loads CSV files from a local `data` directory and presents them through a professional, tab-organized interface with extensive interactive visualizations and analytics capabilities.

The dashboard serves as a complete data analytics solution featuring 8 distinct visualization types, advanced filtering systems, skill co-occurrence analysis, demand forecasting, and comprehensive comparison tools. All data sources are completely abstracted from users, maintaining a formal business intelligence presentation.

## Recent Changes (Latest Update)

- **Dream Job Career Roadmap**: Interactive career guidance system with skill requirements, salary expectations, and progression paths for major tech roles
- **Dynamic PDF Reports**: Personalized PDF generation based on user's dream job, target location, and career preferences 
- **Enhanced Subscription System**: PDF reports now include dream job roadmap content and location-specific market insights
- **Team Member Updates**: Updated credits to Om Aravindhashan.S (23MID0222) and Raghul (23MID0322)
- **Career Path Database**: Built-in roadmaps for Data Scientist, Full Stack Developer, ML Engineer, and DevOps Engineer roles
- **Location-Based Analysis**: Target location insights with salary data and company hiring patterns in career roadmaps
- **PDF Export Functionality**: Comprehensive PDF report generation with executive summary, insights, and detailed analytics
- **Email Subscription System**: User email collection with CSV storage and personalized thank you messages
- **Animated Metrics Dashboard**: Dynamic KPI cards showing most frequent skill, top company, hiring location, and salary metrics
- **Smart Insights Engine**: AI-generated market insights with skill percentages, location analysis, and salary trends
- **Enhanced User Experience**: Removed all data loading messages for cleaner professional interface
- **Tab-based UI Restructuring**: Reorganized interface into Overview, Visualizations, and Raw Data tabs
- **Advanced Analytics Implementation**: Added skill co-occurrence analysis, demand saturation index, and trend forecasting
- **Enhanced Filtering System**: Implemented flexible date filtering with month/year options alongside existing filters
- **Theme Support**: Added light/dark theme toggle with comprehensive CSS styling
- **Data Source Abstraction**: Removed all CSV download functionality and source file references
- **Professional Presentation**: Eliminated emojis and implemented formal business interface
- **Search Functionality**: Added full-text search capability in Raw Data tab
- **Team Credits**: Added footer section with team member acknowledgments
- **Bug Fixes**: Resolved temporal trends update issues with improved date handling and chronological sorting

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit - chosen for rapid development of data-driven web applications
- **Visualization Library**: Plotly (Express and Graph Objects) - provides interactive, publication-quality charts
- **Layout**: Wide layout with expanded sidebar for comprehensive dashboard experience
- **Caching Strategy**: Uses Streamlit's `@st.cache_data` decorator for performance optimization

### Backend Architecture
- **Application Type**: Single-file Python application
- **Data Generation**: Synthetic data generation using realistic distributions and pools
- **Processing**: Pandas for data manipulation and analysis
- **Mathematical Operations**: NumPy for numerical computations

## Key Components

### Data Processing Engine
- **Purpose**: Automatically loads and processes CSV files from local `data` directory
- **Multi-file Support**: Handles unlimited CSV files from the data directory
- **Data Directory Setup**: Creates `data` directory if not found and provides setup instructions
- **Data Validation**: 
  - Required columns: Job Title, Tech Skill, Company, Location, Salary (in LPA), Experience Required (in years), Date Posted
  - Automatic data cleaning and standardization
  - Invalid data detection and removal
  - Source file tracking for multi-file processing
- **Data Processing Features**:
  - Automatic directory scanning for CSV files
  - Date parsing with error handling
  - Numeric conversion for salary and experience fields
  - Duplicate and null value management
  - File-by-file processing with status feedback
  - Caching for performance optimization

### Dashboard Modules
1. **Overview Tab**: Key performance indicators, summary metrics, and insights
   - Total job openings, unique skills, companies, and average salary metrics
   - Key insights highlighting top skills, highest-paying skills, and top locations
2. **Visualizations Tab**: Interactive chart selection with 8 analysis types
   - Skills Analysis: Top in-demand skills visualization
   - Salary Analysis: Interactive salary analysis by skill and location
   - Geographic Analysis: Job distribution by location
   - Temporal Trends: Skill demand trends over time with improved date handling
   - Skill Comparison: Side-by-side analysis of two skills with detailed metrics
   - Skill Co-occurrence: Analysis of skills appearing together in job postings
   - Demand Saturation: Ratio of job openings to unique companies per skill
   - Trend Forecasting: Future demand prediction using linear regression
3. **Raw Data Tab**: Searchable data table with filtering capabilities
   - Search functionality across all data fields
   - Clean presentation without internal source file references

### User Interface Features
- **Tab-Based Organization**: Clean separation of Overview, Visualizations, and Raw Data
- **Advanced Filtering System**: 
  - Multi-select skill filtering
  - Location-based filtering
  - Experience range sliders
  - Flexible date filtering (date range or month/year selection)
- **Theme Support**: Light and dark theme toggle with custom CSS styling
- **Search Functionality**: Full-text search across all data fields in Raw Data tab
- **Professional Presentation**: Formal interface with complete data source abstraction
- **Team Credits**: Footer section acknowledging team members (Om Aravindhashan, Raghul)

### Visualization Components
- **Chart Types**: Bar charts, line plots, scatter plots, bubble charts, pie charts
- **Advanced Analytics**: 
  - Skill co-occurrence analysis using combinations
  - Demand saturation index calculations
  - Linear regression-based trend forecasting
  - Statistical comparisons with detailed metrics
- **Interactivity**: Hover tooltips, responsive design, color-coded data, unified hover modes
- **Export Readiness**: PDF export functionality placeholder for future implementation

## Data Flow

1. **Directory Scanning**: Application scans local `data` directory for CSV files
2. **Data Loading**: All CSV files are automatically loaded and validated
3. **Data Validation**: Files are validated for required columns and data integrity
4. **Data Processing**: Raw data is cleaned, standardized, and aggregated based on user selections
5. **Visualization Rendering**: Processed data is fed into Plotly charts for interactive display
6. **User Interaction**: Sidebar controls allow dynamic filtering and customization
7. **Export Pipeline**: Processed data can be downloaded as CSV for external analysis

## Setup Instructions

### Quick Start
1. Create a `data` directory in your project root
2. Place your CSV files containing job market data in the `data` directory
3. Ensure each CSV has the required columns (see Data Processing Engine above)
4. Run the application - it will automatically detect and load your files

## External Dependencies

### Core Libraries
- **streamlit**: Web application framework
- **pandas**: Data manipulation and analysis
- **plotly**: Interactive visualization library
- **numpy**: Numerical computing
- **datetime**: Date and time handling
- **random**: Random data generation
- **io**: Input/output operations

### Data Dependencies
- **Primary Data Source**: User-uploaded CSV files with job market data
- **File Processing**: Multi-file CSV upload and validation system
- **Optional Demo Data**: Small sample dataset for testing purposes
- No database connections required

## Deployment Strategy

### Development Environment
- **Platform**: Compatible with Replit, local Python environments
- **Requirements**: Python 3.7+ with specified dependencies
- **Configuration**: Streamlit configuration set for wide layout and expanded sidebar

### Production Considerations
- **Scalability**: Single-user application, suitable for demonstration purposes
- **Performance**: Caching implemented for data generation to improve response times
- **Resource Usage**: Lightweight application with minimal memory footprint

### Potential Enhancements
- **Database Integration**: Could be extended to connect with real job market data sources
- **Authentication**: No current user management - could be added for multi-user scenarios
- **Real-time Data**: Currently uses static synthetic data - could integrate with live APIs
- **Advanced Analytics**: Foundation exists for ML-based predictions and advanced analytics