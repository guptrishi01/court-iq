"""Local intake web UI for staging SwingVision matches.

Not a general-purpose web app - a thin, single-user front door onto
SwingVisionImportPipeline.ingest()/suggest(), the same pipeline
scripts/import_match.py already uses. Scope is intake plus a read-only
results/notes page; resolving needs_review flags is still a hand-edit-the-
JSON step, matching Part 4's plan.
"""
