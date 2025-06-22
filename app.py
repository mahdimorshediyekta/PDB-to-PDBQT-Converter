import os
import uuid
import time
import atexit
import requests  # Added for making requests to Cloudflare
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openbabel import openbabel
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler

# Load .env file for local development if it exists
# This will load CLOUDFLARE_SECRET_KEY for local testing
load_dotenv()

# --- Configuration ---
TEMP_DIR = 'temp_files'
MAX_CONTENT_LENGTH = 13 * 1024 * 1024  # 13 MB
FILE_LIFETIME_SECONDS = 300  # 5 minutes
CLOUDFLARE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
CLOUDFLARE_SECRET_KEY = os.getenv('CLOUDFLARE_SECRET_KEY')

# Create the temporary directory if it doesn't exist
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# --- CORS Configuration ---
allowed_origins = [
    "https://sciencecodons.com",
    "http://sciencecodons.com"
]
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

# --- Temporary File Cleanup Scheduler ---
scheduler = BackgroundScheduler(daemon=True)

def delete_old_files():
    """Deletes files in the temp directory older than the configured lifetime."""
    try:
        current_time = time.time()
        for filename in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > FILE_LIFETIME_SECONDS:
                    os.remove(file_path)
                    print(f"Deleted old file: {filename}")
    except Exception as e:
        print(f"Error during file cleanup: {e}")

scheduler.add_job(func=delete_old_files, trigger="interval", minutes=5)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# --- CAPTCHA Verification Logic ---
def verify_captcha(token: str):
    """Verifies the Cloudflare Turnstile token."""
    if not CLOUDFLARE_SECRET_KEY:
        print("Warning: CLOUDFLARE_SECRET_KEY is not set. CAPTCHA verification is skipped.")
        # In a production environment, you might want to fail closed instead
        return True 

    try:
        response = requests.post(CLOUDFLARE_VERIFY_URL, data={
            'secret': CLOUDFLARE_SECRET_KEY,
            'response': token,
            # Optionally include the user's IP address
            # 'remoteip': request.remote_addr
        })
        response.raise_for_status()
        result = response.json()
        return result.get('success', False)
    except requests.exceptions.RequestException as e:
        print(f"Error verifying CAPTCHA: {e}")
        return False

# --- PDB to PDBQT Conversion Logic ---
def convert_pdb_to_pdbqt(pdb_data_string: str):
    """
    Parses a PDB string, adds hydrogens, computes Gasteiger charges,
    and returns a PDBQT formatted string or an error.
    """
    try:
        obConversion = openbabel.OBConversion()
        obConversion.SetInAndOutFormats("pdb", "pdbqt")
        mol = openbabel.OBMol()
        if not obConversion.ReadString(mol, pdb_data_string):
             raise ValueError("Failed to read PDB data. The format may be invalid or corrupted.")
        mol.AddHydrogens()
        charge_model = openbabel.OBChargeModel.FindType("gasteiger")
        if charge_model:
            if not charge_model.ComputeCharges(mol):
                raise RuntimeError("Failed to compute Gasteiger charges.")
        else:
            raise RuntimeError("Gasteiger charge model not found in Open Babel library.")
        pdbqt_output = obConversion.WriteString(mol)
        if not pdbqt_output or not pdbqt_output.strip():
            raise ValueError("Conversion resulted in empty PDBQT data, possibly due to an unsupported molecular structure.")
        return pdbqt_output, None
    except Exception as e:
        print(f"Error during PDB to PDBQT conversion: {e}")
        return None, str(e)

# --- API Endpoints ---
@app.route('/api/convert', methods=['POST'])
def handle_conversion():
    """Handles the file upload, conversion, and response."""
    
    # --- CAPTCHA Verification ---
    captcha_token = request.form.get('cf-turnstile-response')
    if not captcha_token:
        return jsonify({"success": False, "error": "CAPTCHA token missing. Please refresh the page."}), 400
    if not verify_captcha(captcha_token):
        return jsonify({"success": False, "error": "CAPTCHA verification failed. You might be a robot."}), 403

    if 'file' not in request.files and 'pdb_data' not in request.form:
        return jsonify({"success": False, "error": "No PDB data provided. Please upload a file or paste PDB data."}), 400

    pdb_data = ""
    try:
        if 'file' in request.files and request.files['file'].filename != '':
            pdb_file = request.files['file']
            if not pdb_file.filename.lower().endswith('.pdb'):
                return jsonify({"success": False, "error": "Invalid file type. Please upload a .pdb file."}), 400
            pdb_data = pdb_file.read().decode('utf-8')
        elif 'pdb_data' in request.form:
            pdb_data = request.form['pdb_data']
        else:
            return jsonify({"success": False, "error": "No PDB data found in the request."}), 400
        if not pdb_data.strip():
            return jsonify({"success": False, "error": "Submitted PDB data is empty."}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Error processing input: {e}"}), 400

    pdbqt_result, error_message = convert_pdb_to_pdbqt(pdb_data)

    if error_message:
        error_response = f"Conversion failed. {error_message}"
        return jsonify({"success": False, "error": error_response}), 400

    unique_filename = f"{uuid.uuid4()}.pdbqt"
    output_path = os.path.join(TEMP_DIR, unique_filename)
    
    try:
        with open(output_path, "w") as f:
            f.write(pdbqt_result)
    except IOError as e:
        print(f"Error writing file to temporary storage: {e}")
        return jsonify({"success": False, "error": "A server error occurred while preparing the file."}), 500

    download_url = request.host_url.rstrip('/') + f"/api/download/{unique_filename}"

    return jsonify({
        "success": True,
        "pdbqt_data": pdbqt_result,
        "download_url": download_url
    })

@app.route('/api/download/<filename>')
def download_converted_file(filename):
    safe_filename = secure_filename(filename)
    if safe_filename != filename:
        return jsonify({"success": False, "error": "Invalid filename."}), 400
    return send_from_directory(TEMP_DIR, safe_filename, as_attachment=True)

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"success": False, "error": f"The file is too large. The maximum allowed size is {MAX_CONTENT_LENGTH / 1024 / 1024:.0f}MB."}), 413

@app.route('/')
def serve_index():
    return "PDB to PDBQT Converter API is running."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)