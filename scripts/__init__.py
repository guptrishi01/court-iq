"""Entry-point scripts. Not a library package - nothing under src/, ai/, or
reports/ imports from here. This is the one place real, money-spending
clients (Anthropic) actually get constructed; everywhere else takes one
injected.
"""
