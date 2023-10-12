#!/bin/bash
ext1=.tpl
ext2=.html.j2

TEMPLATES_DIR=/opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/templates
for i in $TEMPLATES_DIR/*; do  mv $i ${i/$ext1/$ext2}; done
for i in $TEMPLATES_DIR/*; do sed -i 's/\.tpl/\.html.j2/g' $i; done

FORMGRADER_FILE=/opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/formgrader.py
sed -i 's/HTMLExporter\.template_path\ =\ \[handlers\.template_path\]/HTMLExporter\.template_paths\.append(handlers\.template_path)/g'  $FORMGRADER_FILE

FEEDBACK_FILE=/opt/conda/lib/python3.11/site-packages/nbgrader/converters/generate_feedback.py
sed -i 's/\.tpl/\.html.j2/g' $FEEDBACK_FILE
sed -i 's/basic\.html\.j2/base\.html\.j2/g' $FEEDBACK_FILE
sed -i 's/664/660/g' $FEEDBACK_FILE
sed -i 's/644/640/g' $FEEDBACK_FILE

FEEDBACK_TEMPLATE=/opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/templates/feedback.html.j2
sed -i 's/basic\.html\.j2/base\.html\.j2/g' $FEEDBACK_TEMPLATE

FORMGRADE_FILE=/opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/templates/formgrade.html.j2
sed -i 's/basic\.html\.j2/base\.html\.j2/g' $FORMGRADE_FILE

BASE_FILE=/opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/base.py
sed -i 's/\.tpl/\.html.j2/g' $BASE_FILE

HANDLERS_FILE=/opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/handlers.py
sed -i 's/\.tpl/\.html.j2/g' $HANDLERS_FILE

FORMGRADER_FILE=/opt/conda/lib/python3.11/site-packages/nbgrader/server_extensions/formgrader/formgrader.py
sed -i 's/\.tpl/\.html.j2/g' $FORMGRADER_FILE

API_FILE=/opt/conda/lib/python3.11/site-packages/nbgrader/apps/api.py
sed -i 's/\.tpl/\.html.j2/g' $API_FILE

