# 🚀 Layered Progressive Career Strategy System

An AI-powered career decision system for Data & AI roles —  
designed to guide users from **macro opportunity → industry → company strategy → job → growth**,  
instead of starting directly from job applications.

---

## 🔻 Career Strategy Funnel

<p align="center">
  <img src="career_strategy_funnel.png" width="500"/>
</p>

---

## 💡 What This Project Does

Most job search tools start from **resumes and job postings**.

This system takes a fundamentally different approach:

> Start from **where opportunity exists**, then move down to execution.

It helps answer:

- 🌍 Which **regions and policies** support long-term opportunities?
- 🧭 Which **industries** are worth entering?
- 🏢 What **types of companies** should you target (not just names)?
- 🎯 What **role path** makes sense given your background?
- 📄 How to **align your experience with a specific job (JD)**?
- 🚀 How to build a **growth plan and compelling application narrative**?

---

## 🧠 Core Philosophy

This system follows a **top-down decision framework**:

Policy / Region
↓
Industry Prioritization
↓
Company Strategy
↓
Role Path Design
↓
Job Alignment (JD)
↓
Growth & Application Assets


Unlike traditional tools, this system focuses on:

- **Industry-first decision making**
- **Company strategy over company lists**
- **Positioning & value creation (not just matching)**
- **Long-term career growth, not just short-term offers**

---

## ⚙️ System Architecture (High-Level)

- **Policy Engine** → Macro signals, visa constraints, regional opportunities  
- **Industry Engine** → Industry scoring (growth, fit, entry feasibility)  
- **Company Strategy Engine** → Market, company archetype, competitiveness, stage, value chain, competitors  
- **Role Path Engine** → Ideal / bridge / stretch roles  
- **Job Targeting Engine** → JD analysis, alignment, gap, positioning  
- **Growth Engine** → 30-60-90 days plan, value creation, narrative  

---

## 🔮 Vision

To evolve into a **career decision intelligence system** that:

- Goes beyond job matching
- Helps users **choose the right industry and company**
- Translates experience into **market-valued positioning**
- Provides **actionable growth strategies**


---

## ▶️ Local Usage

After pulling this repo locally, create and activate a virtual environment, install dependencies with `pip install -r requirements.txt`, and run the project with `python -m src.main`. This project now runs as an LLM-only pipeline: Gemini is required, policy and company discovery use grounded search by default, and the system no longer falls back to local deterministic baselines. After the Industry step, the CLI will also collect explicit company-environment preferences so the Company Strategy stage can balance user intent with competitiveness analysis. Add **your own** `GEMINI_API_KEY` to `.env`; successful runs will save the session output to `outputs/interactive_career_state.json`.
