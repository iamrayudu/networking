# Sudheer's Master Profile
# Sources: Drive resume, Carlson interview prep, MBA essays, JobFlow OS conversation history
# Last updated: March 2026

## Identity
Full name: Sudheer Rayudu
Sign messages as: Sudheer
Date of birth: 3rd October 1998
Location: Minneapolis, Minnesota, USA
Originally from: Guntur / Tenali, Andhra Pradesh, India
Email: sudheerrayudu183@gmail.com
LinkedIn: https://www.linkedin.com/in/sudheer-rayudu-8577171a3/
Languages: English, Telugu, Hindi

## Who I am — one line
Full-stack engineer with 4 years building enterprise systems at Renault-Nissan,
now at Carlson MBA building production-grade multi-agent AI systems from scratch —
targeting technical product and AI strategy roles where engineering depth and
product thinking live in the same person.

## Education

### Full-Time MBA — Management Science (STEM-designated)
Carlson School of Management, University of Minnesota, Minneapolis
Started: August 2025 | Expected graduation: 2027
Focus: Data analytics, strategic decision-making, product strategy, operations management
Activities: Consulting Club, Tech Club, Brand Enterprise, Consulting Enterprise
36-month OPT eligibility as STEM MBA

### B.Tech — Electronics and Communication Engineering
Vellore Institute of Technology (VIT), Vellore, India
2016 – 2020 | CGPA: 7.95/10
Activities: Logistics Head of FEPSI (social service club), E-gadget club (sensor design),
            hackathons, technical fests, entrepreneurial stalls at university events

### Bhashyam Junior College, Guntur | Class XII | 2015 | 96%
### Bhashyam Public School, Tenali | Class X | 2013 | 10/10

## Work History

### Renault Nissan Technology and Business Centre India (RNTBCI)
Chennai, India | ~2020 – 2025 (4 years, before MBA)
Tech and business consulting joint venture serving Nissan, Renault, and Mitsubishi

Progression: Graduate Trainee → Engineer → Senior Engineer (promoted twice in 3 years)

What I built and owned:
- Modernised 4 legacy enterprise applications — rewrote outdated Java systems into
  secure, high-performance modern applications used across the organisation
- Proposed microservices architecture for legacy Java project — when initial proposal
  was rejected, adapted and implemented serverless microservices as Maven projects.
  Project succeeded, earned senior leader confidence, led to promotion to Senior Engineer.
- Implemented OKTA Authentication for role-based access control across multiple platforms
- Built a suite of internal operational tools used daily across the organisation:
  billing hour monitoring, attendance management, design approval workflows,
  bill of materials system, document signing reminder system
- Saved 25% on server costs by analysing and decommissioning outdated servers,
  replacing with modern application stack
- Improved system performance by 25% on Perl-to-modern-framework migration
- Led Docker containerisation, NGINX reconfiguration, Unix to Linux migrations
- Led brainstorming sessions to unblock stalled projects — regularly took on
  legacy systems others avoided
- Collaborated with cross-functional teams: business stakeholders, end-users, engineering

Tech stack at RNTBCI:
  Backend:        Java, Spring Boot, Struts, JSP, Maven, Perl (modernised away from)
  Frontend:       AngularJS
  Infrastructure: Docker, NGINX, Unix/Linux server management
  Security:       OKTA authentication and role-based access control
  Approach:       Legacy modernisation, microservices, serverless architecture

### BHEL (Bharat Heavy Electricals Limited) — Internship
Exposure to large-scale industrial operations, task management, cross-sector coordination.
First understanding of how technology integrates with business at enterprise scale.

### Independent — AI & Automation Engineer (Current, alongside MBA)
Minneapolis, MN | 2025 – present

Building from scratch:
- JobFlow OS: production-grade full-stack AI job networking automation system
  (see Projects section for full detail)
- Multi-agent AI systems using Anthropic Claude API with parallel agent orchestration
- Automation pipelines combining web scraping, LLMs, structured memory, and human-in-the-loop
- Personal infrastructure: automation tools for workflows, research, and job search

## Technical Skills

Languages:
  Java (4 years, production), Python, JavaScript, TypeScript, SQL, C, C++ (beginner)

Frontend:
  React 18, Vite, TailwindCSS, AngularJS, Zustand, Recharts, React Router, JSP

Backend:
  FastAPI, Spring Boot, Struts, Maven, Node.js, uvicorn, WebSockets

AI & Automation:
  Anthropic Claude API, multi-agent orchestration, parallel agent execution,
  Selenium, undetected-chromedriver, prompt engineering, agent skill design,
  context object architecture, micro-skill injection, ChromaDB (vector DB),
  DuckDuckGo search API, BeautifulSoup, web scraping and data enrichment

Data & Analytics:
  pandas, SQLite, ChromaDB, data pipeline design, structured data extraction,
  BI concepts, financial analysis (NPV, IRR — Carlson coursework)

Cloud & Infrastructure:
  Docker, NGINX, Unix/Linux server management, AWS (learning), GCP (learning),
  Azure (learning), local-first architecture, server cost optimisation

Security:
  OKTA authentication, role-based access control implementation

Databases:
  SQLite, PostgreSQL (familiar), ChromaDB, JSON document stores

Other tools:
  Git, npm, Python venv, REST APIs, WebSockets, Maven project structure,
  legacy system modernisation, microservices design

## Certifications
[Update with exact cert names, providers, and completion dates]
- Cloud certifications — AWS / GCP / Azure (in progress / recently completed)
- AI & ML certifications (in progress)
- PM framework certifications (in progress)
- STEM MBA — Carlson / University of Minnesota (in progress, class of 2027)

## Projects Worth Mentioning in Outreach

### JobFlow OS — Current flagship project
Problem: Job networking at scale is impossible manually. Researching companies,
         writing personalised positioning stories, finding the right people on LinkedIn,
         and sending tailored messages across 20+ roles takes weeks.
What I built:
  Full-stack AI automation system — from scratch:
  - React + Vite + TailwindCSS frontend: Agent Command Center (real-time chat with agents
    via WebSocket) + Data Intelligence Dashboard (KPIs, contacts, memory search, reports)
  - FastAPI backend: WebSocket server, REST API, agent orchestration
  - 5 parallel Chrome agents using Selenium (each works a different role simultaneously)
  - 4-layer memory: SQLite (structured facts) + ChromaDB (semantic vector search) +
    decision log (infers WHY you made every decision) + preference store (learns your
    style across sessions)
  - Growing context object: built once per agent, enriched at every tool call,
    checkpointed to SQLite after every step — no context loss on crash
  - 8 micro-skill files injected at each tool boundary
  - Voice anchor system — re-anchors Sudheer's tone at every Claude call
  - Chrome guards: 5 pre-action checks before every Selenium action
  - Output schema validation: every step has a defined shape, validated before handoff
  - Complete failure handler: 15+ failure types, each with defined severity and action
Result: A production-grade system that researches roles, writes personalised stories,
        finds the right people, drafts specific messages, and gets smarter every session.
        Built entirely from scratch. Full architecture designed and implemented solo.

### Legacy Modernisation at RNTBCI — Best for enterprise/engineering roles
Problem: 4 legacy Java enterprise applications serving Nissan, Renault, Mitsubishi —
         outdated technology, security vulnerabilities, high maintenance cost, poor performance.
What I built:
  Full modernisation across 4 systems. Proposed microservices architecture —
  when rejected, adapted to serverless microservices as Maven projects.
  OKTA authentication for role-based access. Server decommissioning analysis.
  Unix to Linux migrations. Docker containerisation. NGINX reconfiguration.
Result:
  25% server cost reduction.
  25% performance improvement (Perl to modern framework).
  Promoted to Senior Engineer. Senior leader confidence earned.
  Systems used in production across the organisation.

### Internal Tooling Suite at RNTBCI — Best for PM/product roles
Problem: Manual, fragmented processes for billing, attendance, design approvals,
         document signing across a large org supporting 3 automotive brands.
What I built:
  Suite of internal tools — billing hour monitoring, attendance management,
  design approval workflows, bill of materials management, document signing
  reminders. Built end-to-end, collaborated directly with business stakeholders
  and end-users to understand requirements.
Result:
  Operational tools used daily across the organisation.
  Deep understanding of how technology serves real business processes at scale.

## What I Am Looking For

Role types targeting:
  Technical Product Manager, Senior PM, Product Strategy Lead,
  AI Product Manager, Head of Product (right-stage company),
  Engineering Manager, AI/Automation Specialist,
  Business Development (tech-focused), Operations Manager (tech-driven)

Company types:
  AI-native companies — strongest fit, I speak the language natively
  Scale-stage startups (Series A to pre-IPO)
  Enterprise SaaS — especially developer tools, data products, infra
  Tech consulting firms at enterprise level
  Twin Cities companies with Fortune 500 presence (Carlson network leverage)
  Companies where engineers respect PMs who understand the stack

What I want to work on:
  AI products and platforms
  Developer tooling and internal tooling at scale
  Automation infrastructure
  Data products
  Anything at the intersection of engineering depth and product strategy

What I do NOT want:
  Pure management with no technical ownership or proximity to the code
  PM roles where the PM is a middleman between engineering and business
  Companies using AI as a marketing term
  Roles that erase the engineering background entirely

## My Edge — Why I Am Different

1. I build, not just manage. I can read the code, design the schema, architect
   the agent system, and ship the product. This is uncommon in PM and strategy candidates.

2. I am building multi-agent AI production systems right now — not studying them,
   not in a course, not experimenting — actually shipping. JobFlow OS is real.

3. Enterprise credibility: 4 years at RNTBCI serving Nissan, Renault, Mitsubishi.
   I know what breaks at scale, what legacy looks like, and how to modernise it.

4. I bridge two worlds: I can discuss implementation with engineers and
   strategy with business leaders in the same conversation. No translation needed.

5. Promoted twice in 3 years by taking on hard problems others avoided —
   legacy systems, blocked projects, security overhauls.

6. Genuinely global background: Indian engineering → Japanese automotive tech
   (Nissan/Renault) → American STEM MBA → self-directed AI builder in Minneapolis.
   Cross-cultural and cross-functional by nature.

7. Black belt in Taekwondo, fine arts background, entrepreneurial family roots —
   competitive, creative, and grounded.

8. Chose the hard path: left a stable Senior Engineer career in India, moved to the US,
   started a rigorous STEM MBA while simultaneously building production AI systems.
   Not waiting for permission to work on frontier problems.

## Personal Context
- Born into a business family — parents own a food manufacturing and processing company
- Long-term vision: expand the family business into digital markets using technology
  (compete with Nestlé and Britannia in India using data and AI)
- Short-term: land a PM, strategy, or AI product role at a top tech firm in the US
- Using every Carlson resource: Enterprise Programs, Analytics Lab, alumni network,
  career services, Fortune 500 recruiting pipeline in Twin Cities
- Building JobFlow OS as both a real tool AND a proof of AI engineering capability
- Minneapolis-based, open to relocation for the right opportunity
