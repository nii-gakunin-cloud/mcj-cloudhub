#!/bin/bash
FEEDBACK_FILE=/opt/conda/lib/python3.11/site-packages/nbgrader/converters/generate_feedback.py
sed -i 's/664/660/g' $FEEDBACK_FILE
sed -i 's/644/640/g' $FEEDBACK_FILE
