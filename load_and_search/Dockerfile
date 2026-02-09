FROM gcr.io/dataflow-templates-base/python311-template-launcher-base

ARG WORKDIR=/dataflow/template
RUN mkdir -p ${WORKDIR}
WORKDIR ${WORKDIR}

# 1. Copy requirements to a TEMPORARY location (not the final WORKDIR)
COPY load_and_search/requirements.txt /tmp/requirements.txt

# 2. Install dependencies from the temp file
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 3. Copy pipeline code
COPY load_and_search/ .

# 5. Copy schema file
COPY queries/bq_schema.json /dataflow/queries/bq_schema.json

# 6. Set environment variable for the Flex Template Launcher (Entrypoint)
ENV FLEX_TEMPLATE_PYTHON_PY_FILE="${WORKDIR}/dataflow_pipeline.py"
ENV PYTHONPATH="${WORKDIR}:${PYTHONPATH}"
