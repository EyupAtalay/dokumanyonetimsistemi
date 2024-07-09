from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from pymongo import MongoClient
import gridfs
from bson import ObjectId

app = Flask(__name__)
app.secret_key = "supersecretkey"

# MongoDB bağlantısı
client = MongoClient('mongodb://localhost:27017/')
db = client['file_db']
fs = gridfs.GridFS(db)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    fs.put(file, filename=file.filename)
    flash('File successfully uploaded')
    return redirect(url_for('index'))

@app.route('/files')
def list_files():
    files = fs.find()
    return render_template('list_files.html', files=files)

@app.route('/download/<file_id>')
def download(file_id):
    file = fs.get(ObjectId(file_id))
    return send_file(file, download_name=file.filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)