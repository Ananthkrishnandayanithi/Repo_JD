**README.md**

# GitHub Repository Analyzer

## Overview
GitHub Repository Analyzer is a Streamlit-based application that evaluates GitHub repositories for technical capabilities, project quality, and job description (JD) alignment. The tool fetches repository details, analyzes commit activity, detects technologies used, and provides a suitability score for job candidates.

## Features
- Fetch repositories from a GitHub user profile
- Retrieve and analyze repository README, file structure, and commit activity
- Match repository details with a provided job description using Google Gemini AI
- Provide a detailed breakdown of technologies, algorithms, and complexity
- Generate a final candidate suitability score

## Technologies Used
- **Streamlit** for the web application interface
- **GitHub API** for fetching repository details
- **Google Gemini AI** for analyzing repository content and JD matching
- **LangChain** for handling AI-generated prompts

## Installation
### Prerequisites
Ensure you have Python 3.8 or later installed.

### Steps
1. Clone this repository:
   ```sh
   git clone https://github.com/your-username/github-repo-analyzer.git
   cd github-repo-analyzer
   ```
2. Create a virtual environment (optional but recommended):
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

## Usage
1. Create a `.env` file and add your API keys:
   ```sh
   GITHUB_TOKEN=your_github_token
   GEMINI_API_KEY=your_google_gemini_api_key
   ```
2. Run the application:
   ```sh
   streamlit run app.py
   ```
3. Enter your GitHub username, API keys, and job description in the UI to start the analysis.

## Environment Variables
- `GITHUB_TOKEN`: GitHub API token for accessing repositories
- `GEMINI_API_KEY`: Google Gemini AI API key for analyzing repository data

## Requirements
See `requirements.txt` for all dependencies.

## License
This project is licensed under the MIT License.

---

**requirements.txt**

```
streamlit
requests
time
json
google-generativeai
langchain-core
langchain-google-genai
dotenv
```

