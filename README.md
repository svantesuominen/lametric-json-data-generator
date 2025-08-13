# lametric-json-data-generator

A small Flask service that fetches live Alepa bike availability from the Digitransit API and returns LaMetric-compatible JSON.

## Local Run
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set your DIGITRANSIT_KEY
python app.py
