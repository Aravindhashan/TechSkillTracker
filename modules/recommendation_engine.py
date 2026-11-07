import pandas as pd
import numpy as np
from itertools import combinations


def build_cooccurrence_matrix(df):
    """
    Build skill co-occurrence matrix based on company hiring patterns
    Assumes companies hiring multiple skills together indicates complementary skills
    """
    # Group skills by company
    company_skills = df.groupby('Company')['Tech Skill'].apply(list).reset_index()
    
    # Get all unique skills
    all_skills = sorted(df['Tech Skill'].unique())
    
    # Initialize co-occurrence matrix
    cooccurrence = pd.DataFrame(0, index=all_skills, columns=all_skills)
    
    # Count co-occurrences
    for skills_list in company_skills['Tech Skill']:
        unique_skills = list(set(skills_list))
        if len(unique_skills) > 1:
            for skill1, skill2 in combinations(unique_skills, 2):
                cooccurrence.loc[skill1, skill2] += 1
                cooccurrence.loc[skill2, skill1] += 1  # Symmetric matrix
    
    return cooccurrence


def recommend_skills(df, current_skill, top_n=5):
    """
    Recommend complementary skills based on co-occurrence analysis
    """
    cooccurrence_matrix = build_cooccurrence_matrix(df)
    
    if current_skill not in cooccurrence_matrix.index:
        return [], f"No recommendations available for {current_skill}"
    
    # Get skills that co-occur with current skill
    skill_scores = cooccurrence_matrix[current_skill].sort_values(ascending=False)
    
    # Exclude the skill itself and get top N
    recommendations = skill_scores[skill_scores.index != current_skill].head(top_n)
    
    if recommendations.empty or recommendations.sum() == 0:
        return [], f"No strong skill associations found for {current_skill}"
    
    # Format recommendations with scores
    recs = []
    for skill, score in recommendations.items():
        if score > 0:
            skill_data = df[df['Tech Skill'] == skill]
            
            recs.append({
                'skill': skill,
                'co_occurrence_score': int(score),
                'job_count': len(skill_data)
            })
    
    return recs, "success"


def recommend_for_job_role(df, job_role, top_n=10):
    """
    Recommend skills for a specific job role based on market data
    """
    # Find jobs matching the role (case-insensitive partial match)
    matching_jobs = df[df['Job Title'].str.contains(job_role, case=False, na=False)]
    
    if len(matching_jobs) == 0:
        # Try to find similar roles
        similar_roles = df['Job Title'].str.lower().unique()
        similar = [role for role in similar_roles if any(word in role for word in job_role.lower().split())]
        
        if similar:
            return [], f"No exact match for '{job_role}'. Similar roles found: {', '.join(similar[:3])}"
        return [], f"No data found for job role '{job_role}'"
    
    # Get skill frequency for matching jobs
    skill_analysis = matching_jobs.groupby('Tech Skill').agg({
        'Job Title': 'count',
    }).reset_index()
    
    skill_analysis.columns = ['skill', 'frequency']
    skill_analysis = skill_analysis.sort_values('frequency', ascending=False).head(top_n)
    
    recommendations = []
    for _, row in skill_analysis.iterrows():
        recommendations.append({
            'skill': row['skill'],
            'frequency': int(row['frequency']),
            'percentage': (row['frequency'] / len(matching_jobs)) * 100
        })
    
    return recommendations, "success"


def get_skill_pairs(df, min_cooccurrence=2):
    """
    Get top skill pairs that frequently appear together
    """
    company_skills = df.groupby('Company')['Tech Skill'].apply(list).reset_index()
    
    pair_counts = {}
    
    for skills_list in company_skills['Tech Skill']:
        unique_skills = list(set(skills_list))
        if len(unique_skills) > 1:
            for skill1, skill2 in combinations(sorted(unique_skills), 2):
                pair = (skill1, skill2)
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
    
    # Filter and sort
    filtered_pairs = {k: v for k, v in pair_counts.items() if v >= min_cooccurrence}
    sorted_pairs = sorted(filtered_pairs.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_pairs[:20]  # Top 20 pairs


def get_learning_path(df, current_skills, target_role):
    """
    Generate a learning path from current skills to target role
    """
    # Get recommended skills for target role
    target_skills, status = recommend_for_job_role(df, target_role, top_n=15)
    
    if not target_skills:
        return None, status
    
    # Identify skills to learn (not in current skills)
    current_skills_lower = [s.lower().strip() for s in current_skills]
    skills_to_learn = []
    
    for skill_info in target_skills:
        if skill_info['skill'].lower().strip() not in current_skills_lower:
            skills_to_learn.append(skill_info)
    
    # Prioritize by frequency
    if skills_to_learn:
        skills_to_learn.sort(key=lambda x: x['frequency'], reverse=True)
    
    return skills_to_learn, "success"
