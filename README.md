# 🚀 Layered Progressive Career Strategy System

An AI-powered career decision system for Data & AI roles —  
designed to guide users from **macro opportunity → industry → company strategy → job → growth**,  
instead of starting directly from job applications.

---

## Career Strategy Funnel

<p align="center">
  <img src="Diagram.png" width="500"/>
</p>

---

## What This Project Does

This project is a Layered Progressive Career Strategy System, built to feel like a smart career advisor that walks with you through every step of your job search. What makes it powerful is that every step is driven by a large language model, and each step connects to the next—so instead of random suggestions, you get a clear, continuous path. You start by telling the system about yourself—your education, skills, projects, and even real-world constraints like visa status. From there, the system thinks step by step: it helps you choose the right industries, points you to the kinds of companies you should focus on, matches you with realistic roles, and even helps you prepare resumes, cover letters, and networking messages. Along the way, it explains why each decision makes sense, so you’re not just following advice—you’re learning how to think strategically about your career. In simple terms, this isn’t just a tool to find jobs; it’s a complete AI-powered career planning journey where every part is connected, helping you go from feeling unsure to having a clear, confident plan.

---

## Local Usage

After pulling this repo locally, create and activate a virtual environment, install dependencies with `pip install -r requirements.txt`, add **your own** `GEMINI_API_KEY` to `.env`, and then run either the CLI or the local web app.

The project is now resume-scanning-first. Instead of relying on a hard-coded local profile, the system scans a resume, lets you review the extracted fields, and then walks through the layered strategy flow stage by stage.

CLI:

`python -m src.main --resume /path/to/resume.pdf`

If you omit `--resume`, the CLI will prompt for a file path. You can also prefill it with `CAREER_RESUME_PATH`.

Supported resume import paths currently prioritize `pdf`, image files, and `doc/docx` files in the local macOS environment. Runtime artifacts are written under `outputs/`, which is intentionally kept out of version control.

To run the local web upload portal instead of the CLI:

`python -m src.web_app`

Then open `http://127.0.0.1:5000` in your browser, upload a resume, and move through the strategy funnel stage by stage in the browser: Policy, Industry, Company Preference, Company Strategy, Role Path, optional Job Alignment, Growth Plan, and optional Application Assets. The web flow presents each stage in natural language instead of raw JSON while still saving workflow checkpoints and analysis artifacts under `outputs/`.
