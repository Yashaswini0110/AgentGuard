# AgentGuard

flowchart TD
    %% ── ENTRY ──
    ATS(["🏢 Enterprise ATS\nApplicant Tracking System"])
    AGENT["🤖 Hiring AI Worker Agent\nOutputs structured JSON decision\ncandidate_id · score · features_used · confidence"]

    ATS -->|"Candidate application feed"| AGENT

    %% ── AGENTGUARD BOUNDARY ──
    subgraph AG["🛡️  AgentGuard v3 — Governance Control Plane"]
        direction TB

        INTERCEPT["⛔ Interception Gateway\nEvery decision STOPPED here\nbefore any execution"]

        %% LAYER 1
        subgraph L1["Layer 1 — Deterministic Policy Engine  •  < 5ms  •  Zero AI"]
            direction LR
            PE["📋 Hard Rule Checker\nPython rule dictionary\nBinary PASS / BLOCK"]
            R1["🚫 BLOCK: emotion_score used\nEU AI Act Article 5 — flat prohibition"]
            R2["🚫 BLOCK: applicant_surname used\nCaste / religion proxy — India law"]
            R3["🚫 BLOCK: institution_tier used\nSocioeconomic / caste proxy"]
            R4["🚫 BLOCK: career_gap + gender\nMaternity discrimination proxy"]
            R5["🚫 BLOCK: home_district / village_code\nTribal identity proxy"]
            R6["🚫 BLOCK: prompt injection detected\nSecurity rule"]
            PE --> R1 & R2 & R3 & R4 & R5 & R6
        end

        %% LAYER 2
        subgraph L2["Layer 2 — Explainable Risk Router  •  < 50ms  •  sklearn GBClassifier"]
            direction LR
            ROUTER["⚡ Risk Classifier\nFeatures: experience · skill_match\ninterview_score · assessment_score\nconfidence · feature_count"]
            SHAP["📊 SHAP Explainer\nPer-feature importance scores\nEmbedded in every artifact\n(router only — not LLM)"]
            ROUTER --> SHAP
        end

        %% THREE PATHS
        GREEN["✅ GREEN\nAuto-Execute\nNo LLM · No cost\n< 50ms"]
        YELLOW["🟡 YELLOW\nSupervisor Review\nGPT-4o-mini semantic check\nProxy discrimination scan"]
        RED["🔴 RED\nHard Block\nPENDING state\nHuman required"]

        %% LAYER 3
        subgraph L3["Layer 3 — System of Record Commit"]
            SN["🎫 ServiceNow REST API\nReal incident ticket created\ne.g. INC0004821\nDecision held until ID returns"]
            HOLD["⏸️ Execution Hold\n5-second timeout\nAuto-block if no response"]
            SN --> HOLD
        end

        %% ARTIFACT
        subgraph ART["Signed Decision Artifact Engine  •  Every Decision"]
            direction LR
            ARTGEN["🔏 SHA-256 Artifact Generator\ndecision_id · timestamp · candidate_id\npolicy_rule_cited · routing_classification\nconfidence_score · features_used\nshap_scores · model_version_hash\nservicenow_ticket_id · artifact_hash"]
        end

        %% HUMAN
        HUMAN["👤 HR Compliance Officer\nReviews RED queue\nApprove / Reject / Override\nAll overrides logged in artifact"]

        INTERCEPT --> L1
        L1 -->|"PASS"| L2
        L1 -->|"BLOCK → RED"| RED
        L2 --> GREEN & YELLOW & RED
        RED --> L3
        L3 --> HUMAN
        HUMAN -->|"Decision + reason logged"| ART
        GREEN --> ART
        YELLOW --> ART
        RED --> ART
    end

    %% ── OUTPUTS ──
    EXEC["✅ Decision Executed\nATS updated\nCandidate notified"]
    AUDITDB[("🗄️ Immutable Audit Log\nPostgreSQL\nAll artifacts stored")]
    REGEXPORT["📄 Regulatory Export\nOne-click JSON download\nEU AI Act Technical Doc\nDPDP Act evidence file"]
    DASH["📈 Governance Dashboard\nLive decision feed GREEN/YELLOW/RED\nLatency benchmarks · Drift detection\nToken cost savings"]

    GREEN -->|"Auto-execute"| EXEC
    YELLOW -->|"Approved"| EXEC
    HUMAN -->|"Approved"| EXEC
    ART --> AUDITDB
    AUDITDB --> REGEXPORT
    AUDITDB --> DASH

    %% ── DEMO CASES ──
    subgraph DEMO["🎬 Live Demo — 3 Test Cases"]
        direction LR
        CA["Case A — GREEN ✅\nRahul Sharma\nSkill match 0.89 · No violations\nExecuted in 31ms"]
        CB["Case B — YELLOW 🟡\nAnjali Verma\nConfidence 0.58 · Ambiguous weighting\nSupervisor review triggered"]
        CC["Case C — RED 🔴\nMeena Devi · Chandrapur\nemotion_score + institution_tier used\nArticle 5 violation · INC ticket fires"]
    end

    AGENT --> INTERCEPT
    DEMO -.->|"Simulated inputs"| AGENT

    %% ── STYLES ──
    classDef entry fill:#1F4E79,stroke:#1F4E79,color:#fff,rx:8
    classDef block fill:#8B0000,stroke:#8B0000,color:#fff
    classDef green fill:#1E7A3E,stroke:#1E7A3E,color:#fff
    classDef yellow fill:#7B4F00,stroke:#7B4F00,color:#fff
    classDef red fill:#8B0000,stroke:#8B0000,color:#fff
    classDef artifact fill:#2E4057,stroke:#2E4057,color:#fff
    classDef output fill:#0D47A1,stroke:#0D47A1,color:#fff
    classDef demo fill:#4A235A,stroke:#4A235A,color:#fff
    classDef human fill:#1B5E20,stroke:#1B5E20,color:#fff

    class ATS,AGENT entry
    class R1,R2,R3,R4,R5,R6 block
    class GREEN green
    class YELLOW yellow
    class RED,HOLD red
    class ARTGEN,ART artifact
    class EXEC,AUDITDB,REGEXPORT,DASH output
    class CA,CB,CC demo
    class HUMAN human
