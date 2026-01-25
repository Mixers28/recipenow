# Documentation Index - Sprint 2-3 (OCR Enhancement + LLM Vision Fallback)

**Quick Navigation:** Use this index to find the right document for your role/question.

---

## For Different Roles

### 👔 Product Manager / Stakeholder
**Start here:** [SPEC.md](SPEC.md) → [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

**Questions answered:**
- What's the new functionality? → IMPLEMENTATION_SUMMARY.md (Architecture section)
- When's it ready? → HANDOFF.md (Success Criteria)
- What's the risk? → HANDOFF.md (Risk Level)
- Next steps? → SPEC.md (Sprints 4-6)

---

### 🧪 QA / Testing Team
**Start here:** [QUICK_START.md](QUICK_START.md) → [TESTING_GUIDE.md](TESTING_GUIDE.md)

**Questions answered:**
- How do I test this? → TESTING_GUIDE.md (complete guide)
- How do I set up? → QUICK_START.md (5-minute setup)
- What should pass? → HANDOFF.md (Success Criteria)
- What could go wrong? → TESTING_GUIDE.md (Troubleshooting)

**Key Files:**
1. [QUICK_START.md](QUICK_START.md) - 5-minute setup
2. [TESTING_GUIDE.md](TESTING_GUIDE.md) - Unit + integration + manual tests
3. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Smoke tests post-deployment

---

### 👨‍💻 Backend Developer (Testing Phase)
**Start here:** [QUICK_START.md](QUICK_START.md) → [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md)

**Questions answered:**
- What was implemented? → IMPLEMENTATION_PROGRESS.md (What Was Implemented)
- How do I run tests? → TESTING_GUIDE.md (Unit Tests)
- What's broken? → README error logs → TESTING_GUIDE.md (Troubleshooting)
- How do I debug? → TESTING_GUIDE.md (Debug Rotation Detection)

**Key Code Files:**
- [apps/api/services/ocr.py](../apps/api/services/ocr.py) - Rotation detection
- [apps/api/services/llm_vision.py](../apps/api/services/llm_vision.py) - LLM fallback
- [apps/api/worker/jobs.py](../apps/api/worker/jobs.py) - Job pipeline

---

### 🚀 DevOps / Deployment Engineer
**Start here:** [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

**Questions answered:**
- What do I deploy? → DEPLOYMENT_CHECKLIST.md (Deployment Steps)
- What could break? → DEPLOYMENT_CHECKLIST.md (Known Issues & Mitigations)
- How do I verify? → DEPLOYMENT_CHECKLIST.md (Smoke Tests & Monitoring)
- How do I rollback? → DEPLOYMENT_CHECKLIST.md (Rollback Plan)

**Key Operations:**
1. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Step-by-step deployment
2. [QUICK_START.md](QUICK_START.md) - System dependency installation
3. `infra/migrations/002_add_source_method.sql` - Database migration

---

### 👨‍💼 Tech Lead / Architect
**Start here:** [SPEC.md](SPEC.md) → [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) → [HANDOFF.md](HANDOFF.md)

**Questions answered:**
- What's the architecture? → SPEC.md (Architecture section) + IMPLEMENTATION_PROGRESS.md (Architecture Overview)
- What were trade-offs? → IMPLEMENTATION_PROGRESS.md (Key Design Decisions)
- Is it production-ready? → HANDOFF.md (Success Criteria + Risk Level)
- What's next? → SPEC.md (Sprints 4-6)

**Decision Documents:**
- [SPEC.md](SPEC.md) - Canonical specification
- [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) - Design decisions
- [HANDOFF.md](HANDOFF.md) - Pre-deployment checklist

---

### 🎯 Frontend Developer (Next Sprint)
**Start here:** [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md#UI) → SPEC.md (Sprint 5)

**Questions answered:**
- What UI do I need to build? → SPEC.md (Review UI section, Sprint 5)
- What data do I have? → IMPLEMENTATION_PROGRESS.md (SourceSpan with source_method)
- How do I display badges? → SPEC.md (Badge specification)
- What APIs do I call? → SPEC.md (Data flow & interfaces)

**Next Sprint Tasks:**
- Implement source badges (OCR=blue, LLM=purple, User=green, Missing=red)
- Display SourceSpan.source_method in RecipeForm
- Allow field overrides by user

---

## Document Guide

### 📋 Reference Documents (Canonical)

#### [SPEC.md](SPEC.md)
**The Source of Truth**
- Architecture overview
- Invariants & constraints (9 total)
- Two-stage OCR pipeline specification
- Rotation detection algorithm
- LLM vision fallback design
- Sprint-by-sprint implementation plan
- Acceptance criteria for each ticket

**When to use:** All implementation decisions must align with SPEC.md

---

### 📚 Implementation Documents

#### [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md)
**What Was Built**
- Detailed breakdown of changes to each file
- Architecture diagrams
- Key design decisions
- Testing checklist
- Known limitations & mitigations
- Remaining sprints

**When to use:** Understanding what code was implemented and why

#### [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
**Executive Summary**
- 60-second overview
- What changed and why
- Performance benchmarks
- Breaking changes (none)
- Review checklist

**When to use:** Quick summary for stakeholders or team leads

---

### 🧪 Testing Documents

#### [TESTING_GUIDE.md](TESTING_GUIDE.md)
**Complete Testing Instructions**
- Prerequisites (system dependencies, Python packages)
- Unit tests for OCR, LLM, jobs
- Integration end-to-end tests
- Manual testing procedures
- Performance benchmarks
- Troubleshooting guide

**When to use:** Setting up tests or debugging failures

---

### 🚀 Deployment Documents

#### [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
**Safe Deployment Steps**
- Pre-deployment verification
- Step-by-step deployment
- Environment configuration
- System tool installation
- Smoke tests
- Post-deployment monitoring
- Rollback plan

**When to use:** Deploying to production or staging

---

### ⚡ Quick Reference

#### [QUICK_START.md](QUICK_START.md)
**5-Minute Setup + Common Tasks**
- 60-second overview
- Installation (5 minutes)
- Testing (10 minutes)
- Configuration
- Common tasks with code examples
- Troubleshooting

**When to use:** Getting up to speed quickly or solving immediate problems

---

### 🤝 Handoff Documents

#### [HANDOFF.md](HANDOFF.md)
**Phase Transition Summary**
- What was delivered
- File changes summary
- Architecture overview
- System requirements
- Deployment path
- Known limitations
- Success criteria
- Sign-off checklist

**When to use:** End-of-sprint handoff, code review, approval gates

---

### 📊 Progress Tracking

#### [NOW.md](NOW.md)
**Current Sprint Status**
- What we're working on right now
- Completed vs. in-progress vs. pending
- Current blockers
- Next immediate steps

**When to use:** Daily standup, sprint planning, status updates

---

## Document Dependencies

```
SPEC.md (canonical source of truth)
├─ IMPLEMENTATION_PROGRESS.md (what was built)
│  ├─ TESTING_GUIDE.md (how to test it)
│  └─ DEPLOYMENT_CHECKLIST.md (how to deploy it)
├─ IMPLEMENTATION_SUMMARY.md (executive summary)
├─ HANDOFF.md (phase transition)
├─ QUICK_START.md (quick reference)
└─ NOW.md (sprint progress)
```

---

## Common Questions & Quick Answers

### "Where's the architecture?"
→ SPEC.md (Architecture section) or IMPLEMENTATION_PROGRESS.md (Architecture Overview)

### "How do I test this?"
→ TESTING_GUIDE.md (entire document)

### "How do I deploy this?"
→ DEPLOYMENT_CHECKLIST.md (entire document)

### "What code changed?"
→ IMPLEMENTATION_PROGRESS.md (Files Modified section) or git diff

### "Is it production-ready?"
→ HANDOFF.md (Success Criteria + Risk Level)

### "What's the next sprint?"
→ SPEC.md (Sprints 4-6) or NOW.md

### "How do I set this up?"
→ QUICK_START.md (Installation section)

### "What's broken?"
→ TESTING_GUIDE.md (Troubleshooting section)

### "What's the status?"
→ NOW.md (Current Objective section)

### "Can I disable this?"
→ QUICK_START.md (Emergency Disable section)

### "What about the UI?"
→ SPEC.md (Sprint 5 - Review UI) or frontend team docs

---

## Document Maintenance

### Update Frequency
- **SPEC.md:** Only for major architectural changes (managed by Architect)
- **IMPLEMENTATION_PROGRESS.md:** Updated at sprint completion (managed by Coder)
- **NOW.md:** Updated at standup (managed by Scrum Master)
- **TESTING_GUIDE.md:** Updated as new tests added (managed by QA)
- **DEPLOYMENT_CHECKLIST.md:** Updated as deployment procedure evolves (managed by DevOps)
- **QUICK_START.md:** Updated as setup process simplifies (managed by DevOps)

### Versioning
- All documents marked with SPEC.md version (currently: 2.1)
- Update version when making breaking changes
- Changelog tracked in git commit messages

---

## Getting Started Paths

### I'm new to RecipeNow
1. Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) (5 min)
2. Read [QUICK_START.md](QUICK_START.md) (10 min)
3. Set up environment per QUICK_START.md (5 min)
4. Run tests per TESTING_GUIDE.md (15 min)

**Total: ~35 minutes to be productive**

### I need to test this
1. Read [QUICK_START.md](QUICK_START.md) (10 min)
2. Follow installation (5 min)
3. Read [TESTING_GUIDE.md](TESTING_GUIDE.md) (20 min)
4. Run tests (30 min)

**Total: ~65 minutes to complete QA**

### I need to deploy this
1. Read [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) (20 min)
2. Follow pre-deployment verification (15 min)
3. Follow deployment steps (30 min)
4. Run smoke tests (15 min)

**Total: ~80 minutes to deploy to production**

### I need to understand the architecture
1. Read [SPEC.md](SPEC.md) - Architecture section (20 min)
2. Read [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) - Architecture Overview (10 min)
3. Review code files:
   - apps/api/services/ocr.py (15 min)
   - apps/api/services/llm_vision.py (20 min)
   - apps/api/worker/jobs.py (25 min)

**Total: ~90 minutes to master the architecture**

---

## Table of Contents (by Topic)

### OCR Implementation
- SPEC.md → OCR Enhancement section
- IMPLEMENTATION_PROGRESS.md → OCRService with Rotation Detection
- TESTING_GUIDE.md → Test Rotation Detection
- QUICK_START.md → Test Rotation Detection

### LLM Vision Fallback
- SPEC.md → LLM Vision Fallback section
- IMPLEMENTATION_PROGRESS.md → LLMVisionService
- TESTING_GUIDE.md → Test LLM Vision Service
- QUICK_START.md → Test LLM Extraction

### Job Pipeline
- SPEC.md → Job Design & Triggers
- IMPLEMENTATION_PROGRESS.md → Job Implementation Suite
- TESTING_GUIDE.md → Test Job Functions
- QUICK_START.md → Test Job Pipeline

### Database Schema
- SPEC.md → Data flow & interfaces
- IMPLEMENTATION_PROGRESS.md → Database Schema Updates
- DEPLOYMENT_CHECKLIST.md → Database Migration

### Deployment
- DEPLOYMENT_CHECKLIST.md (entire document)
- QUICK_START.md → Installation

### Testing
- TESTING_GUIDE.md (entire document)
- QUICK_START.md → Testing section

---

## Key Contacts

For questions about:
- **Architecture:** See SPEC.md and Architect agent notes
- **OCR Implementation:** See IMPLEMENTATION_PROGRESS.md (OCRService section)
- **LLM Integration:** See IMPLEMENTATION_PROGRESS.md (LLMVisionService section)
- **Testing:** See TESTING_GUIDE.md
- **Deployment:** See DEPLOYMENT_CHECKLIST.md
- **General:** See QUICK_START.md

---

## Version Information

- **SPEC.md Version:** 2.1 (OCR Enhancement + LLM Vision Fallback)
- **Sprint:** 2-3 (Ingest & OCR, Structure & Normalize)
- **Python Version:** 3.10+
- **Last Updated:** Sprint 2-3 Completion
- **Status:** ✅ Code Complete → Ready for Testing

---

**Happy coding!** Start with the document for your role above. 🚀
