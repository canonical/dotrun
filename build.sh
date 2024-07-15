#!/bin/bash
poetry build
pip uninstall -y dotrun
pip install --no-index --find-links dist/ dotrun