import pandas as pd
import numpy as np

def generate_safe_features(n_samples=5000):
    """
    Generate the safe features used for ML training.
    """
    # years_of_experience: 0-25, right-skewed (more early-career candidates)
    # Mirrors NASSCOM/ILO India Employment Report 2024 showing high youth participation
    yoe = np.random.gamma(shape=1.5, scale=3.0, size=n_samples)
    yoe = np.clip(yoe, 0, 25).round(1)
    
    # base skill_match (0-1)
    skill_match_score = np.random.beta(a=4, b=2, size=n_samples)
    
    # assessment_score (0-100) correlated with skill_match_score
    # Adding some random noise
    assessment_noise = np.random.normal(loc=0, scale=10, size=n_samples)
    assessment_score = np.clip((skill_match_score * 100) + assessment_noise, 0, 100).round(1)
    
    # interview_score (0-10) correlated with skill_match_score
    interview_noise = np.random.normal(loc=0, scale=1.5, size=n_samples)
    interview_score = np.clip((skill_match_score * 10) + interview_noise, 0, 10).round(1)
    
    # decision_confidence (0-1) Higher performance scores -> higher confidence
    norm_score = (skill_match_score + (assessment_score / 100) + (interview_score / 10)) / 3
    decision_confidence = np.clip(norm_score + np.random.normal(0, 0.1, size=n_samples), 0, 1).round(3)
    
    # feature_count (3-15) - slightly increases with complexity/experience
    feature_count = np.clip(np.random.poisson(lam=5 + (yoe / 5)), 3, 15).astype(int)
    
    return pd.DataFrame({
        'years_of_experience': yoe,
        'skill_match_score': skill_match_score.round(3),
        'assessment_score': assessment_score,
        'interview_score': interview_score,
        'decision_confidence': decision_confidence,
        'feature_count': feature_count
    })

def generate_bias_features(n_samples=5000):
    """
    Generate prohibited/bias features for policy testing.
    Reflects Indian labor market context and structural inequalities.
    """
    # institution_tier (1-4)
    # Tier 3 & 4 dominate, creating a proxy for socio-economic background
    institution_tier = np.random.choice([1, 2, 3, 4], p=[0.05, 0.15, 0.40, 0.40], size=n_samples)
    
    # career_gap_months (0-36) - simulates gaps (e.g., maternity, preparation for competitive exams)
    has_gap = np.random.binomial(1, 0.35, size=n_samples)
    career_gap_months = np.clip(np.random.exponential(scale=10, size=n_samples) * has_gap, 0, 36).astype(int)
    
    # applicant_surname (realistic Indian surnames across regions/communities)
    surnames = ['Sharma', 'Verma', 'Gupta', 'Patil', 'Deshmukh', 'Kumar', 'Singh', 'Yadav', 'Paswan', 'Munda', 'Meena', 'Iyer', 'Menon', 'Das', 'Banerjee', 'Ansari', 'Khan']
    applicant_surname = np.random.choice(surnames, size=n_samples)
    
    # emotion_score (0-1) - typically collected via visual AI, prohibited by EU AI Act Article 5
    emotion_score = np.random.beta(a=5, b=2, size=n_samples).round(3) 
    
    # home_district
    districts = ['Bengaluru Urban', 'Mumbai Suburban', 'Pune', 'Hyderabad', 'Bastar', 'Gaya', 'Kalahandi', 'Mewat']
    # 60% urban/developed, 40% rural/less-developed (bias triggers)
    home_district = np.random.choice(districts, p=[0.20, 0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.10], size=n_samples)
    
    # caste_indicator
    caste_indicator = np.random.choice(['General', 'OBC', 'SC', 'ST'], p=[0.30, 0.40, 0.20, 0.10], size=n_samples)
    
    return pd.DataFrame({
        'institution_tier': institution_tier,
        'career_gap_months': career_gap_months,
        'applicant_surname': applicant_surname,
        'emotion_score': emotion_score,
        'home_district': home_district,
        'caste_indicator': caste_indicator
    })

def inject_bias(df):
    """
    Inject structural bias intentionally to simulate real-world flawed AI models.
    The AI system has implicitly learned to penalize based on proxies.
    """
    np.random.seed(42)  # For reproducible perturbations
    
    # 1. Institution Tier Bias: Penalty for Tier 3/4 colleges
    tier_penalty = (df['institution_tier'] >= 3).astype(int) * 0.05
    df['skill_match_score'] = np.clip(df['skill_match_score'] - tier_penalty, 0, 1).round(3)
    
    # 2. Career Gap Bias: Simulates penalization for maternity/health gaps
    gap_penalty = (df['career_gap_months'] > 6).astype(int) * 0.08
    df['skill_match_score'] = np.clip(df['skill_match_score'] - gap_penalty, 0, 1).round(3)
    
    # 3. Geographic & Caste Proxy Bias: Slight negative bias for less developed districts
    rural_districts = ['Bastar', 'Gaya', 'Kalahandi', 'Mewat']
    rural_penalty = df['home_district'].isin(rural_districts).astype(int) * 5.0
    df['assessment_score'] = np.clip(df['assessment_score'] - rural_penalty, 0, 100).round(1)
    
    # 4. Emotion Score Bias: Illegal usage violating EU AI Act
    # Lower emotion score penalizes interview score (simulating pseudo-science 'culture fit' algorithms)
    emotion_penalty = (df['emotion_score'] < 0.5).astype(int) * 1.5
    df['interview_score'] = np.clip(df['interview_score'] - emotion_penalty, 0, 10).round(1)
    
    # Recompute decision confidence to reflect the new, biased scores
    norm_score = (df['skill_match_score'] + (df['assessment_score'] / 100) + (df['interview_score'] / 10)) / 3
    df['decision_confidence'] = np.clip(norm_score + np.random.normal(0, 0.05, size=len(df)), 0, 1).round(3)
    
    return df

def assign_labels(df):
    """
    Generate risk_label (GREEN, YELLOW, RED) based on rules + probabilities.
    Thresholds are dynamically set to ensure GREEN: ~75%, YELLOW: ~17%, RED: ~8% distribution.
    """
    # Create an aggregate risk score based on heuristic AI Governance rules:
    
    # Bias triggers count
    bias_trigger_count = (
        (df['institution_tier'] >= 3).astype(int) +
        (df['career_gap_months'] > 12).astype(int) +
        df['home_district'].isin(['Bastar', 'Gaya', 'Kalahandi', 'Mewat']).astype(int) +
        (df['emotion_score'] < 0.4).astype(int) # Unusual emotion
    )
    
    # High bias triggers + Low confidence = High Risk (RED)
    # Moderate issues OR unusual feature combinations = Medium Risk (YELLOW)
    risk_score = (
        (1.0 - df['decision_confidence']) * 10 +  # Heavy penalty for low prediction confidence
        bias_trigger_count * 2.5 +                # Penalty for triggering bias variables
        (df['feature_count'] > 12).astype(int) * 1.0 # Slight penalty for unusual feature complexity
    )
    
    # Define thresholds to match class distribution constraints
    # RED: top 8% risk scores
    # YELLOW: next 17% risk scores
    # GREEN: bottom 75% risk scores
    q_yellow = risk_score.quantile(0.75)
    q_red = risk_score.quantile(0.92)
    
    conditions = [
        risk_score >= q_red,
        risk_score >= q_yellow
    ]
    choices = ['RED', 'YELLOW']
    df['risk_label'] = np.select(conditions, choices, default='GREEN')
    
    return df

def main():
    np.random.seed(42) # Ensure full reproducibility
    n_samples = 5000
    
    print("Generating safe features...")
    df_safe = generate_safe_features(n_samples)
    
    print("Generating prohibited/bias features...")
    df_bias = generate_bias_features(n_samples)
    
    # Combine feature sets
    df = pd.concat([df_safe, df_bias], axis=1)
    
    print("Injecting algorithmic biases...")
    df = inject_bias(df)
    
    print("Assigning governance risk labels (GREEN/YELLOW/RED)...")
    df = assign_labels(df)
    
    # Reorder columns logically
    cols = [
        'years_of_experience', 'skill_match_score', 'assessment_score', 
        'interview_score', 'decision_confidence', 'feature_count',
        'institution_tier', 'career_gap_months', 'applicant_surname', 
        'emotion_score', 'home_district', 'caste_indicator', 'risk_label'
    ]
    df = df[cols]
    
    # Save to CSV
    output_filename = "synthetic_hr_dataset.csv"
    df.to_csv(output_filename, index=False)
    
    # Print Outcomes
    print("\n" + "="*40)
    print("--- Class Distribution ---")
    dist = df['risk_label'].value_counts(normalize=True) * 100
    for label, pct in dist.items():
        print(f"{label}: {pct:.2f}%")
        
    print("\n--- Basic Statistics Summary ---")
    print(f"Total Rows: {len(df)}")
    print(f"Total Columns: {len(df.columns)}")
    print(f"Dataset generated and saved to: {output_filename}")
    print("="*40)
    
    print("\nNumerical Features Summary:")
    print(df[['skill_match_score', 'assessment_score', 'interview_score', 'decision_confidence', 'career_gap_months']].describe().round(2))

if __name__ == "__main__":
    main()
