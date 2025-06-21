import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests as req
from openbabel import openbabel
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

# --- Configuration ---
# CLOUDFLARE_SECRET_KEY is no longer needed.

TEMP_DIR = 'temp_files'
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

# --- PDB to PDBQT Conversion Logic ---
def convert_pdb_to_pdbqt(pdb_data_string: str):
    """
    Parses a PDB string, adds hydrogens, computes Gasteiger charges,
    and returns a PDBQT formatted string.
    """
    try:
        obConversion = openbabel.OBConversion()
        obConversion.SetInAndOutFormats("pdb", "pdbqt")

        mol = openbabel.OBMol()
        obConversion.ReadString(mol, pdb_data_string)

        # Add hydrogen atoms
        mol.AddHydrogens()

        # Calculate Gasteiger partial charges (essential for PDBQT)
        charge_model = openbabel.OBChargeModel.FindType("gasteiger")
        if charge_model:
            charge_model.ComputeCharges(mol)
        
        pdbqt_output = obConversion.WriteString(mol)
        return pdbqt_output

    except Exception as e:
        print(f"Error during PDB to PDBQT conversion: {e}")
        return None

# --- API Endpoints ---
@app.route('/api/convert', methods=['POST'])
def handle_conversion():
    """
    Handles the main conversion request from the frontend.
    """
    # CAPTCHA verification has been removed.

    pdb_data = ""
    if 'file' in request.files and request.files['file'].filename != '':
        pdb_file = request.files['file']
        pdb_data = pdb_file.read().decode('utf-8')
    elif 'pdb_data' in request.form and request.form['pdb_data'].strip() != '':
        pdb_data = request.form['pdb_data']
    else:
        return jsonify({"success": False, "error": "No PDB data provided."}), 400

    pdbqt_result = convert_pdb_to_pdbqt(pdb_data)

    if not pdbqt_result or not pdbqt_result.strip():
        return jsonify({"success": False, "error": "Conversion failed. The provided data may not be a valid PDB format."}), 400

    unique_filename = f"{uuid.uuid4()}.pdbqt"
    output_path = os.path.join(TEMP_DIR, unique_filename)
    with open(output_path, "w") as f:
        f.write(pdbqt_result)

    return jsonify({
        "success": True,
        "pdbqt_data": pdbqt_result,
        "download_url": f"/api/download/{unique_filename}"
    })

@app.route('/api/download/<filename>')
def download_converted_file(filename):
    """
    Serves the converted file for download.
    """
    return send_from_directory(TEMP_DIR, filename, as_attachment=True)

@app.route('/')
def serve_index():
    """
    Serves the index.html file for the root URL.
    """
    return send_from_directory('.', 'index.html')


# --- Main Entry Point ---
if __name__ == '__main__':
    app.run(port=5000, debug=True)
