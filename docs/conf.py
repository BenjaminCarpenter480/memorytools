import os
import sys
sys.path.insert(0, os.path.abspath('../memorytools'))

from sphinx.ext import autodoc, autosummary, doctest, intersphinx
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'MemoryTools'
copyright = '2024, Benjamin Carpenter'
author = 'Benjamin Carpenter'
release = '0.99'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['myst_parser','sphinx.ext.autodoc', 'sphinx.ext.autosummary', 'sphinx.ext.intersphinx' ]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
