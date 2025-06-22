<<<<<<< HEAD
# PDB to PDBQT Converter API

This is a Flask-based backend API for converting Protein Data Bank (`.pdb`) files to the AutoDock Vina (`.pdbqt`) format. It is designed to be deployed as a containerized service on platforms like Google Cloud Run.

## Features

- **Bot Protection**: Integrated with Cloudflare Turnstile CAPTCHA to prevent abuse.
- **File and Text Input**: Accepts PDB data either as a file upload or as pasted text.
- **Robust Conversion**: Uses the Open Babel library to reliably add hydrogens and compute Gasteiger charges.
- **File Size Limit**: Enforces a 13MB limit on input file size.
- **Automatic Cleanup**: Temporary PDBQT files are automatically deleted after 5 minutes.
- **CORS Enabled**: Configured to accept requests specifically from `sciencecodons.com`.
- **Dockerized**: Includes a `Dockerfile` for easy, reproducible builds and deployments.
- **Cloud Ready**: Optimized for deployment on Google Cloud Run, using Gunicorn for production.

## CAPTCHA Setup (Required)

This service uses Cloudflare Turnstile to protect against automated submissions.

1.  **Get Keys**: Sign up for a free Cloudflare account and create a new Turnstile site. You will receive a **Site Key** (for your frontend) and a **Secret Key** (for this backend).
2.  **Set Environment Variable**: You **must** set the `CLOUDFLARE_SECRET_KEY` environment variable in your deployment environment (e.g., in the Google Cloud Run service settings).
    ```
    CLOUDFLARE_SECRET_KEY=YOUR_CLOUDFLARE_SECRET_KEY
    ```
3.  **Frontend Integration**: Your website frontend must include the Turnstile widget and send the generated token as `cf-turnstile-response` in the form data of the POST request to `/api/convert`.

## API Endpoint

### `POST /api/convert`

**Request (multipart/form-data):**

-   `cf-turnstile-response`: The CAPTCHA token from the frontend. **(Required)**
-   `file`: The `.pdb` file to be converted.
-   OR `pdb_data`: A string containing the raw PDB data.

**Success Response (200 OK):**

```json
{
  "success": true,
  "pdbqt_data": "...",
  "download_url": "https://your-service-url/api/download/some-unique-id.pdbqt"
}

Local Development
Clone the repository.

Create .env file: Create a file named .env in the project root and add your secret key:

CLOUDFLARE_SECRET_KEY="1x0000000000000000000000000000000AA"

(Note: For local testing, you can use the test keys provided by Cloudflare that always pass or fail without real verification)

Create a virtual environment:

python -m venv venv
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Run the development server:

python app.py

Deployment to Google Cloud Run
Make sure you have the Google Cloud SDK installed.

Deploy from the root of the project directory:

gcloud run deploy pdb-converter-api --source . --region YOUR_REGION --allow-unauthenticated

Set the secret environment variable in Cloud Run:

gcloud run services update pdb-converter-api --region YOUR_REGION --set-env-vars CLOUDFLARE_SECRET_KEY="YOUR_REAL_SECRET_KEY"
=======
