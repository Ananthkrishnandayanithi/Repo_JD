import streamlit as st
import requests
import time
import json
import google.generativeai as genai
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAI
from dotenv import load_dotenv

# Configure page
st.set_page_config(
    page_title="GitHub Repository Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Add custom CSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .repo-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border: 1px solid #e6e6e6;
    }
    .stTextArea textarea {
        height: 200px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'github_token' not in st.session_state:
    st.session_state.github_token = ""
if 'gemini_key' not in st.session_state:
    st.session_state.gemini_key = ""

def initialize_api(github_token, gemini_key):
    """Initialize API configurations"""
    try:
        headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
        
        # Configure Gemini API
        genai.configure(api_key=gemini_key)
        llm = GoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2, google_api_key=gemini_key)
        
        # Test the configuration
        test_response = llm.invoke("Test")
        return headers, llm
    except Exception as e:
        st.error(f"Error initializing APIs: {str(e)}")
        st.error("Please ensure your API keys are correct and try again.")
        return None, None

def get_github_repos(username, headers):
    """Fetch repositories from a user's GitHub profile."""
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch repositories. Status code: {response.status_code}")
        return []

def get_repo_details(username, repo_name, headers):
    """Fetch README, latest commits, and repo structure."""
    readme_url = f"https://api.github.com/repos/{username}/{repo_name}/readme"
    commits_url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
    contents_url = f"https://api.github.com/repos/{username}/{repo_name}/contents"
    languages_url = f"https://api.github.com/repos/{username}/{repo_name}/languages"

    readme_content = ""
    commit_messages = []
    file_structure = []
    languages_used = []

    with st.spinner(f"Fetching details for {repo_name}..."):
        # Fetch README
        readme_response = requests.get(readme_url, headers=headers)
        if readme_response.status_code == 200:
            readme_content = requests.get(readme_response.json()['download_url']).text

        # Fetch latest 5 commits
        commit_response = requests.get(commits_url, headers=headers)
        if commit_response.status_code == 200:
            commit_messages = [commit['commit']['message'] for commit in commit_response.json()[:5]]

        # Fetch file structure
        content_response = requests.get(contents_url, headers=headers)
        if content_response.status_code == 200:
            file_structure = [file['name'] for file in content_response.json()]

        # Fetch languages used
        lang_response = requests.get(languages_url, headers=headers)
        if lang_response.status_code == 200:
            languages_used = list(lang_response.json().keys())

    return readme_content, commit_messages, file_structure, languages_used

def analyze_repo_and_jd_match(readme, file_structure, commits, languages, jd, llm):
    """Use Gemini AI to analyze repository and match with JD."""
    prompt_template = PromptTemplate(
        input_variables=["readme", "files", "commits", "languages", "jd"],
        template="""
        You are an AI technical recruiter. Analyze the following GitHub project details and job description:
        
        Job Description:
        {jd}
        
        Repository Details:
        README: {readme}
        File Structure: {files}
        Commit Messages: {commits}
        Languages: {languages}
        
        Provide output as structured JSON:
        {{
            "languages": ["list of languages"],
            "tech_stack": ["list of frameworks & libraries"],
            "algorithms": ["list of key algorithms used"],
            "complexity": "low/medium/high",
            "commit_activity": "active/moderate/inactive",
            "jd_match_score": "1-100",
            "jd_match_reasons": ["list of reasons why this repository matches or doesn't match the JD"]
        }}
        """
    )

    try:
        response = llm.invoke(prompt_template.format(
            readme=readme, 
            files=", ".join(file_structure),
            commits=", ".join(commits), 
            languages=", ".join(languages),
            jd=jd
        ))
        
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        json_data = json.loads(response[json_start:json_end].strip())
        
        return json_data

    except Exception as e:
        st.error(f"Error analyzing repository: {e}")
        return {
            "languages": [],
            "tech_stack": [],
            "algorithms": [],
            "complexity": "unknown",
            "commit_activity": "unknown",
            "jd_match_score": 0,
            "jd_match_reasons": []
        }

def calculate_repo_score(analysis_data):
    """Calculate a score for a repository based on its analysis and JD match."""
    base_score = 0
    
    # Score based on number of languages (max 10 points)
    base_score += min(len(analysis_data['languages']) * 2, 10)
    
    # Score based on tech stack (max 15 points)
    base_score += min(len(analysis_data['tech_stack']) * 3, 15)
    
    # Score based on algorithms (max 15 points)
    base_score += min(len(analysis_data['algorithms']) * 3, 15)
    
    # Score based on complexity (max 30 points)
    complexity_scores = {"low": 10, "medium": 20, "high": 30, "unknown": 0}
    base_score += complexity_scores.get(analysis_data['complexity'].lower(), 0)
    
    # Score based on commit activity (max 30 points)
    activity_scores = {"inactive": 10, "moderate": 20, "active": 30, "unknown": 0}
    base_score += activity_scores.get(analysis_data['commit_activity'].lower(), 0)
    
    # Include JD match score in final calculation
    jd_match_score = float(analysis_data.get('jd_match_score', 0))
    
    # Final score is weighted average of base score and JD match score
    final_score = (base_score * 0.6) + (jd_match_score * 0.4)
    
    return round(final_score)

def evaluate_candidate(total_score, num_repos):
    """Evaluate candidate suitability based on average repository score."""
    if num_repos == 0:
        return "Unable to evaluate - no repositories found"
    
    avg_score = total_score / num_repos
    if avg_score >= 75:
        return "Highly Suitable"
    elif avg_score >= 50:
        return "Moderately Suitable"
    elif avg_score >= 25:
        return "Potentially Suitable"
    else:
        return "Not Suitable"

def display_repo_analysis(repo_name, analysis_data, repo_score):
    """Display repository analysis in Streamlit."""
    with st.expander(f"📁 {repo_name} - Score: {repo_score}/100", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🛠 Technical Details")
            st.write("**Languages:**", ", ".join(analysis_data['languages']))
            st.write("**Tech Stack:**", ", ".join(analysis_data['tech_stack']) if analysis_data['tech_stack'] else "None detected")
            st.write("**Algorithms:**", ", ".join(analysis_data['algorithms']) if analysis_data['algorithms'] else "None detected")
        
        with col2:
            st.markdown("### 📊 Metrics")
            st.write("**Complexity:**", analysis_data['complexity'].capitalize())
            st.write("**Commit Activity:**", analysis_data['commit_activity'].capitalize())
            st.write("**JD Match Score:**", f"{analysis_data.get('jd_match_score', 0)}/100")
            st.progress(repo_score/100)
        
        if analysis_data.get('jd_match_reasons'):
            st.markdown("### 🎯 JD Match Analysis")
            for reason in analysis_data['jd_match_reasons']:
                st.write(f"- {reason}")

def analyze_github_repos(username, headers, llm, jd):
    """Analyze GitHub projects and generate summaries."""
    repos = get_github_repos(username, headers)
    if not repos:
        st.error("No repositories found or failed to fetch repositories.")
        return []

    results = []
    total_score = 0
    progress_bar = st.progress(0)

    for idx, repo in enumerate(repos):
        repo_name = repo['name']
        with st.spinner(f"Analyzing {repo_name}..."):
            readme, commits, file_structure, languages = get_repo_details(username, repo_name, headers)
            analysis_data = analyze_repo_and_jd_match(readme, file_structure, commits, languages, jd, llm)
            repo_score = calculate_repo_score(analysis_data)
            total_score += repo_score
            results.append((repo_name, analysis_data, repo_score))
            
        progress_bar.progress((idx + 1) / len(repos))
        time.sleep(1)

    progress_bar.empty()
    return results, total_score

def main():
    st.title("🔍 GitHub Repository Analyzer")
    st.markdown("""
    This tool analyzes GitHub repositories to evaluate technical capabilities and project quality.
    Please provide the required information below to begin the analysis.
    """)

    # API Keys input
    with st.expander("🔑 API Configuration", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            github_token = st.text_input("GitHub Token", type="password", 
                                       value=st.session_state.get('github_token', ''))
        with col2:
            gemini_key = st.text_input("Google Gemini API Key", type="password",
                                     value=st.session_state.get('gemini_key', ''))

    # Job Description input
    st.subheader("📝 Job Description")
    jd = st.text_area("Paste the job description here", height=200)

    # GitHub username input
    username = st.text_input("👤 Enter GitHub Username")

    # Save API keys to session state
    if github_token:
        st.session_state.github_token = github_token
    if gemini_key:
        st.session_state.gemini_key = gemini_key

    if st.button("Analyze Repositories") and username and jd and github_token and gemini_key:
        headers, llm = initialize_api(github_token, gemini_key)
        
        if headers and llm:
            with st.spinner("Analyzing repositories..."):
                repo_analysis, total_score = analyze_github_repos(username, headers, llm, jd)
                
                if repo_analysis:
                    num_repos = len(repo_analysis)
                    
                    # Display overall summary
                    st.header("📊 Analysis Summary")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Repositories", num_repos)
                    with col2:
                        avg_score = round(total_score / num_repos if num_repos > 0 else 0)
                        st.metric("Average Repository Score", f"{avg_score}/100")
                    with col3:
                        suitability = evaluate_candidate(total_score, num_repos)
                        st.metric("Candidate Suitability", suitability)
                    
                    # Display individual repository analysis
                    st.header("📁 Repository Details")
                    sorted_analysis = sorted(repo_analysis, key=lambda x: x[2], reverse=True)
                    
                    for repo_name, analysis_data, repo_score in sorted_analysis:
                        display_repo_analysis(repo_name, analysis_data, repo_score)
                    
                    # Export option
                    if st.button("Export Analysis"):
                        export_data = {
                            "username": username,
                            "total_repos": num_repos,
                            "average_score": avg_score,
                            "suitability": suitability,
                            "repositories": [
                                {
                                    "name": repo_name,
                                    "score": repo_score,
                                    "analysis": analysis_data
                                }
                                for repo_name, analysis_data, repo_score in sorted_analysis
                            ]
                        }
                        st.download_button(
                            "Download Analysis Report",
                            data=json.dumps(export_data, indent=2),
                            file_name=f"github_analysis_{username}.json",
                            mime="application/json"
                        )
                else:
                    st.error("No repositories found or analysis failed.")
        else:
            st.error("Failed to initialize APIs. Please check your API keys and try again.")

if __name__ == "__main__":
    main()
