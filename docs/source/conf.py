# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath('..'))


project = 'iBridges'
copyright = '2024, 2025, Utrecht University'
author = 'Christine Staiger, Raoul Schram'
release = '1.5.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.napoleon', "sphinx.ext.autodoc", "sphinx_autodoc_typehints",
              'sphinx_rtd_theme', "sphinx_inline_tabs", "sphinx_copybutton",
              "sphinx.ext.autosummary", "sphinxarg.ext"]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

napoleon_use_param = True
