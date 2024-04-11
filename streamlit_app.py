import streamlit as st
import requests

# Flask API base URL
API_BASE_URL = 'http://127.0.0.1:5000'

st.title('Music Streaming Platform')
st.header('Manage Your Music')

# Function to upload audio file
def upload_audio_file(artist_name, track_name, uploaded_file):
    files = {'uploaded_file': (uploaded_file.name, uploaded_file, 'audio/mpeg')}
    data = {'artistName': artist_name, 'trackName': track_name}
    response = requests.post(f'{API_BASE_URL}/api/audio/upload', files=files, data=data)
    return response.json()

# Function to fetch audio files
def fetch_audio_files(page=1):
    response = requests.get(f'{API_BASE_URL}/api/audio/list', params={'page': page})
    return response.json()

# Function to edit audio file
def edit_audio_file(id, artist_name, track_name):
    data = {'artistName': artist_name, 'trackName': track_name}
    response = requests.put(f'{API_BASE_URL}/api/audio/edit/{id}', json=data)
    return response.json()

# Function to delete audio file
def delete_audio_file(id):
    response = requests.delete(f'{API_BASE_URL}/api/audio/delete/{id}')
    return response.json()

# UI for uploading audio
st.subheader('Upload New Audio File')
artist_name = st.text_input('Artist Name', key='upload_artist')
track_name = st.text_input('Track Name', key='upload_track')
uploaded_file = st.file_uploader('Choose a file', type=['mp3', 'wav', 'mpeg'], key='upload_file')
if st.button('Upload Audio File', key='upload'):
    if uploaded_file is not None:
        result = upload_audio_file(artist_name, track_name, uploaded_file)
        st.write(result)
    else:
        st.error('Please select a file to upload.')

# UI for listing audio
st.subheader('List Audio Files')
page_number = st.number_input('Page Number', min_value=1, value=1, step=1, key='list_page')
list_button = st.button('Fetch List', key='list')
if list_button:
    audio_files = fetch_audio_files(page_number)
    if audio_files['success']:
        for audio in audio_files['data']:
            st.write(f"ID: {audio['_id']}, Artist: {audio['artistName']}, Track: {audio['trackName']}, Path: {audio['filePath']}")
    else:
        st.error('Failed to fetch audio files.')

# UI for editing audio
st.subheader('Edit Audio File')
id_to_edit = st.text_input('Audio File ID to Edit', key='edit_id')
new_artist_name = st.text_input('New Artist Name', key='edit_artist')
new_track_name = st.text_input('New Track Name', key='edit_track')
edit_button = st.button('Edit Audio File', key='edit')
if edit_button:
    result = edit_audio_file(id_to_edit, new_artist_name, new_track_name)
    st.write(result)

# UI for deleting audio
st.subheader('Delete Audio File')
id_to_delete = st.text_input('Audio File ID to Delete', key='delete_id')
delete_button = st.button('Delete Audio File', key='delete')
if delete_button:
    result = delete_audio_file(id_to_delete)
    st.write(result)
