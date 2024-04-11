from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson import ObjectId
from flask import send_from_directory
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS

# MongoDB connection
client = MongoClient("mongodb://dsci551admin:2024_dsci551_groupproject@52.52.64.159:27017")
db = client["MusicalChairs"]

# Directory for storing uploaded files
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'mpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to serve Audio files through Flask
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Current timestamp
        original_filename = secure_filename(file.filename)
        filename, file_extension = os.path.splitext(original_filename)
        unique_filename = f"{filename}_{timestamp}{file_extension}"  # Appending timestamp to filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Calculate hash value to determine collection tag
        hash_value = hash_function(artist_name, track_name)
        collection_tag = f"audio_{hash_value}"
        
        # Construct an absolute URL for the file
        file_url = request.url_root + 'uploads/' + unique_filename
        
        # Insert into a specific 'audio' collection based on hash, including file URL
        audio_data = {
            'artistName': artist_name, 
            'trackName': track_name, 
            'filePath': file_path, 
            'fileUrl': file_url,  # Adding file URL
            'collection_tag': collection_tag
        }
        try:
            # Insert the audio data into the hashed collection
            result = db[collection_tag].insert_one(audio_data)
            
            # Insert reference into metadata collection for easy retrieval
            metadata_entry = {
                'artistName': artist_name,
                'trackName': track_name,
                'fileUrl': file_url,  # Store the accessible URL
                'collection_tag': collection_tag,  # Reference to the specific collection
                'audio_id': result.inserted_id  # Reference to the specific document ID in the hashed collection
            }
            db.metadata.insert_one(metadata_entry)
            
            # Prepare response data
            response_data = {
                '_id': str(result.inserted_id),  # Convert ObjectId to string
                'artistName': artist_name, 
                'trackName': track_name, 
                'filePath': file_path, 
                'fileUrl': file_url
            }
            return jsonify({'success': True, 'message': 'Audio uploaded successfully', 'data': response_data})
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
        # Assuming 'metadata' is your unified collection for storing references to all files.
        audio_metadata = list(db.metadata.find({}, {'_id': 1, 'artistName': 1, 'trackName': 1, 'filePath': 1, 'fileUrl': 1, 'collection_tag': 1}).skip(skip).limit(limit))
        for audio in audio_metadata:
            audio['_id'] = str(audio['_id'])  # Convert ObjectId to string for JSON serialization
        return jsonify({'success': True, 'data': audio_metadata})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# API endpoint for editing audio file metadata
@app.route('/api/audio/edit/<id>', methods=['PUT'])
def edit_audio(id):
    data = request.json
    try:
        # Check if document exists
        existing_doc = db.metadata.find_one({'_id': ObjectId(id)})
        if not existing_doc:
            return jsonify({'success': False, 'message': 'Document not found'})

        # Attempt to update the document
        result = db.metadata.update_one({'_id': ObjectId(id)}, {'$set': data})
        if result.modified_count:
            return jsonify({'success': True, 'message': 'Audio edited successfully'})
        else:
            return jsonify({'success': True, 'message': 'No changes made or document already up to date'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# API endpoint for deleting audio files
@app.route('/api/audio/delete/<id>', methods=['DELETE'])
def delete_audio(id):
    try:
        # Lookup the metadata document
        metadata_doc = db.metadata.find_one({'_id': ObjectId(id)})
        if not metadata_doc:
            return jsonify({'success': False, 'message': 'Metadata document not found'})

        # Use the collection_tag to select the correct collection
        collection_name = metadata_doc['collection_tag']
        audio_collection = db[collection_name]

        # Delete the actual audio document
        audio_delete_result = audio_collection.delete_one({'_id': metadata_doc['audio_id']})
        if audio_delete_result.deleted_count == 0:
            return jsonify({'success': False, 'message': 'Audio document not found in the collection'})

        # Delete the metadata document
        metadata_delete_result = db.metadata.delete_one({'_id': ObjectId(id)})
        if metadata_delete_result.deleted_count:
            return jsonify({'success': True, 'message': 'Audio deleted successfully'})
        else:
            # This else is unlikely to be reached since we already found the document
            return jsonify({'success': False, 'message': 'Failed to delete metadata document'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


if __name__ == '__main__':
    # Create the uploads directory if it does not exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True, port=5000)  # Run the Flask app
