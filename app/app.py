from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from pymongo import MongoClient
import gridfs
from bson import ObjectId

app = Flask(__name__)
app.secret_key = "supersecretkey"


client = MongoClient('mongodb://localhost:27017/')
db = client['file_db']
fs = gridfs.GridFS(db)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('Dosya parçası yok')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('Seçili dosya yok')
        return redirect(request.url)
    fs.put(file, filename=file.filename)
    flash('Dosya başarıyla yüklendi')
    return redirect(url_for('index'))

@app.route('/files')
def list_files():
    files = fs.find()
    return render_template('list_files.html', files=files)

@app.route('/download/<file_id>')
def download(file_id):
    file = fs.get(ObjectId(file_id))
    return send_file(file, download_name=file.filename, as_attachment=True)

@app.route('/update/<file_id>', methods=['GET', 'POST'])
def update(file_id):
    if request.method == 'POST':
        file = request.files['file']
        if file:
            
            fs.delete(ObjectId(file_id))
            
            fs.put(file, filename=file.filename)
            flash('Dosya başarıyla güncellendi')
            return redirect(url_for('list_files'))
    else:
        file = fs.get(ObjectId(file_id))
        return render_template('update_file.html', file=file)

if __name__ == '__main__':
    app.run(debug=True)
