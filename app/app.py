from flask import Flask, render_template, request, jsonify, send_file
from pymongo import MongoClient
import hashlib
import io

app = Flask(__name__)

# MongoDB bağlantısı ve koleksiyon tanımlaması
client = MongoClient('mongodb://localhost:27017/')
db = client['document_management']
documents_collection = db['documents']

# Ana sayfa, dosya yükleme formu
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# Dosya yükleme işlemi
@app.route('/', methods=['POST'])
def upload_file():
    file = request.files['file']
    file_content = file.read()

    # Dosyanın içeriğini SHA-256 ile hashleme
    file_hash = hashlib.sha256(file_content).hexdigest()

    # Veritabanında aynı hash değerine sahip belgeyi kontrol et
    existing_document = documents_collection.find_one({'hash': file_hash})

    if existing_document:
        return jsonify({'message': 'Bu belge zaten var.'}), 400
    else:
        # Yeni belgeyi veritabanına ekle
        document_data = {
            'filename': file.filename,
            'content': file_content,
            'hash': file_hash
        }
        documents_collection.insert_one(document_data)
        return jsonify({'message': 'Belge başarıyla yüklendi.'}), 200

# Yüklenmiş belgeleri listeleme
@app.route('/list_documents', methods=['GET'])
def list_documents():
    documents = list(documents_collection.find({}, {'_id': 0}))  # _id alanını hariç tut

    # HTML içeriğini oluşturma
    html_content = '<h1>Yüklenmiş Belgeler</h1><ul>'
    for doc in documents:
        filename = doc['filename']
        html_content += f'<li><a href="/download/{filename}">{filename}</a></li>'
    html_content += '</ul>'
    
    return html_content

# Belge indirme endpoint'i
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    document = documents_collection.find_one({'filename': filename})
    if document:
        file_content = document['content']
        return send_file(io.BytesIO(file_content),
                         download_name=filename,
                         as_attachment=True)
    else:
        return jsonify({'message': 'Belge bulunamadı.'}), 404

if __name__ == '__main__':
    app.run(debug=True)
