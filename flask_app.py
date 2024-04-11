from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson import ObjectId
import os

app = Flask(__name__)
CORS(app)  # Enable CORS

# MongoDB connection
client = MongoClient("mongodb://dsci551admin:2024_dsci551_groupproject@52.52.64.159:27017")
db = client["MusicalChairs"]

# Directory for storing uploaded files
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'mpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Hash function
def hash_function(artist_name, track_name):
    artist_initial = artist_name[0].upper()  # Get the first character and uppercase
    track_initial = track_name[0].upper()  # Get the first character and uppercase
    total = ord(artist_initial) + ord(track_initial)  # Sum of ASCII values
    return total % 2  # Return remainder of division by 2 (either 0 or 1)

# Function to convert ObjectId to string
def jsonify_mongo(data):
    for document in data:
        if '_id' in document:
            document['_id'] = str(document['_id'])
    return jsonify(data)

# API endpoint for uploading audio files
@app.route('/api/audio/upload', methods=['POST'])
def upload_audio():
    if 'uploaded_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})
    file = request.files['uploaded_file']
    artist_name = request.form.get('artistName', '')
    track_name = request.form.get('trackName', '')
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        data = {'artistName': artist_name, 'trackName': track_name, 'filePath': file_path}
        hash_value = hash_function(artist_name, track_name)  # Calculate hash
        collection_tag = f"audio_{hash_value}"  # Determine collection tag based on hash
        data = {'artistName': artist_name, 'trackName': track_name, 'filePath': file_path, 'collection_tag': collection_tag}
        try:
            result = db.audio.insert_one(data)  # Insert into a single 'audio' collection with a tag
            data['_id'] = str(result.inserted_id)  # Convert ObjectId to string
            return jsonify({'success': True, 'message': 'Audio uploaded successfully', 'data': data})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    return jsonify({'success': False, 'message': 'Invalid file type'})

# API endpoint for listing audio files
@app.route('/api/audio/list', methods=['GET'])
def list_audio():
    page = int(request.args.get('page', 1))
    limit = 10  # Adjust as needed
    skip = (page - 1) * limit
    try:
        # Query the single 'audio' collection without needing to specify a tag
        audio_data = list(db.audio.find({}, {'_id': 1, 'artistName': 1, 'trackName': 1, 'filePath': 1, 'collection_tag': 1}).skip(skip).limit(limit))
        for audio in audio_data:
            audio['_id'] = str(audio['_id'])  # Convert ObjectId to string for JSON serialization
        return jsonify({'success': True, 'data': audio_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# API endpoint for editing audio file metadata
@app.route('/api/audio/edit/<id>', methods=['PUT'])
def edit_audio(id):
    data = request.json
    try:
        result = db.audio.update_one({'_id': ObjectId(id)}, {'$set': data})
        if result.modified_count:
            return jsonify({'success': True, 'message': 'Audio edited successfully'})
        else:
            return jsonify({'success': False, 'message': 'No changes made'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# API endpoint for deleting audio files
@app.route('/api/audio/delete/<id>', methods=['DELETE'])
def delete_audio(id):
    try:
        result = db.audio.delete_one({'_id': ObjectId(id)})
        if result.deleted_count:
            return jsonify({'success': True, 'message': 'Audio deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Audio not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    # Create the uploads directory if it does not exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True, port=5000)  # Run the Flask app
