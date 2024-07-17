from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from pymongo import MongoClient
import gridfs
from bson import ObjectId
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import chardet
from docx import Document
import fitz  # PyMuPDF
import io

app = Flask(__name__)
app.secret_key = "supersecretkey"
client = MongoClient('mongodb://localhost:27017/')
db = client['file_db']
fs = gridfs.GridFS(db)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/benimsayfa', methods=['POST'])
def benimsayfa():
    print("çalışıyor")
    return render_template('benimsayfa.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('Dosya parçası yok')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('Seçili dosya yok')
        return redirect(request.url)

    file_content = file.read()
    text_content = None

    try:
        if file.filename.endswith('.txt'):
            result = chardet.detect(file_content)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'
            text_content = file_content.decode(encoding)
        elif file.filename.endswith('.docx'):
            document = Document(io.BytesIO(file_content))
            text_content = '\n'.join([para.text for para in document.paragraphs])
        elif file.filename.endswith('.pdf'):
            pdf_document = fitz.open(stream=io.BytesIO(file_content), filetype="pdf")
            text_content = ''
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                text_content += page.get_text()
        else:
            flash('Dosya formatı desteklenmiyor')
            return redirect(request.url)
    except Exception as e:
        flash(f'Dosya işlenirken hata oluştu: {str(e)}')
        return redirect(request.url)

    if not text_content:
        flash('Dosya içeriği alınamadı')
        return redirect(request.url)

    files = fs.find()
    for existing_file in files:
        existing_content = fs.get(existing_file._id).read()
        try:
            result = chardet.detect(existing_content)
            encoding = result['encoding'] if result['encoding'] else 'utf-8'
            existing_text_content = existing_content.decode(encoding)
        except UnicodeDecodeError:
            continue  # Skip non-text files
        
        similarity_score = compute_similarity(text_content, existing_text_content)
        if similarity_score > 0.99:
            flash('Dosya zaten mevcut.')
            return redirect(url_for('index'))

    fs.put(file_content, filename=file.filename)
    flash('Dosya başarıyla yüklendi')
    return redirect(url_for('index'))

def compute_similarity(doc1, doc2):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([doc1, doc2])
    cos_sim = cosine_similarity(tfidf_matrix)
    similarity_score = cos_sim[0, 1]
    return similarity_score

@app.route('/files')
def list_files():
    files = fs.find()
    return render_template('list_files.html', files=files)

@app.route('/download/<file_id>')
def download(file_id):
    file = fs.get(ObjectId(file_id))
    response = send_file(io.BytesIO(file.read()), download_name=file.filename, as_attachment=True)
    response.headers['Content-Type'] = 'application/octet-stream; charset=utf-8'
    return response

@app.route('/update/<file_id>', methods=['GET', 'POST'])
def update(file_id):
    if request.method == 'POST':
        file = request.files['file']
        if file:
            fs.delete(ObjectId(file_id))
            fs.put(file.read(), filename=file.filename)
            flash('Dosya başarıyla güncellendi')
            return redirect(url_for('list_files'))
    else:
        file = fs.get(ObjectId(file_id))
        return render_template('update_file.html', file=file)

if __name__ == '__main__':
    app.run(debug=True)
