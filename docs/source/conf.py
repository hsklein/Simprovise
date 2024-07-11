# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
sys.path.insert(0, '../../simprovise')

project = 'Simprovise'
copyright = '2024, Howard Klein'
author = 'Howard Klein'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc'
            , 'sphinx.ext.autosummary'
            , 'sphinx_rtd_theme'
            , 'enum_tools.autoenum'
]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'relations.html',
        'searchbox.html',
        'donate.html',
    ]
}
html_theme_options = {
    'fixed_sidebar': 'true',
    'page_width': 'auto'
}

def setup(app):
    from simprovise.core import apidoc
    app.connect('autodoc-skip-member', apidoc.docskip)

