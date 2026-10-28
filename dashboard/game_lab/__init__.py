"""Explicit offline racing laboratory. Importing it never starts a job.

Torch, Gymnasium and reference learners live in a separate interpreter. The
production GUI must not import the modules that require those dependencies.
"""
