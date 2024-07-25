from bson import ObjectId
from flask import Flask, render_template, request, jsonify, send_file
from pymongo import MongoClient
import hashlib
import io

app = Flask(__name__)

# MongoDB bağlantısı ve koleksiyon tanımlaması
client = MongoClient('mongodb://localhost:27017/')
db = client['dokuman_versiyon']
documents_collection = db['dokuman']

# Ana sayfa, dosya yükleme formu
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

def get_new_versioned_filename(filename):
    # Dosya adı ve uzantısını ayır
    if '.' in filename:
        name, extension = filename.rsplit('.', 1)
        extension = '.' + extension
    else:
        name = filename
        extension = ''
    
    # Versiyon numarasını kontrol et
    if '_v' in name:
        parts = name.rsplit('_v', 1)
        if parts[1].isdigit():
            new_version = int(parts[1]) + 1
            return f"{parts[0]}_v{new_version}{extension}"
    
    # Mevcut versiyonları kontrol et
    existing_versions = list(documents_collection.find({'filename': {'$regex': f'^{name}_v[0-9]+{extension}$'}}))
    
    # Versiyon numarası yoksa ve mevcut versiyon da yoksa v1 ekle
    if not existing_versions:
        return f"{name}_v1{extension}"

    # Mevcut versiyon numaralarını bul ve yeni versiyonu belirle
    version_numbers = []
    for doc in existing_versions:
        parts = doc['filename'].rsplit('_v', 1)
        if len(parts) == 2 and parts[1].split('.')[0].isdigit():
            version_numbers.append(int(parts[1].split('.')[0]))

    if version_numbers:
        new_version = max(version_numbers) + 1
    else:
        new_version = 1

    return f"{name}_v{new_version}{extension}"

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
        # Aynı isimdeki dosyalar için versiyon belirleme
        new_filename = get_new_versioned_filename(file.filename)

        # Yeni belgeyi veritabanına ekle
        document_data = {
            'filename': new_filename,
            'content': file_content,
            'hash': file_hash
        }
        documents_collection.insert_one(document_data)
        return jsonify({'message': f'Belge başarıyla yüklendi: {new_filename}'}), 200

# Yüklenmiş belgeleri listeleme
@app.route('/dosyalar', methods=['GET'])
def list_documents():
    documents = list(documents_collection.find({}, {'_id': 0}))  # _id alanını hariç tut


    
    return render_template('dosyalar.html',documents=documents)

# Belge indirme endpoint'i
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    document = documents_collection.find_one({'filename': filename})
    if document:
        document_id = str(document['_id'])  # _id alanını alıyoruz
        try:
            obj_id = ObjectId(document_id)
        except:
            return jsonify({'message': 'Geçersiz ObjectId.'}), 404

        document = documents_collection.find_one({'_id': obj_id})
        if document:
            file_content = document.get('content')
            if file_content is not None:
                filename = document.get('filename', 'downloaded_file')
                return send_file(io.BytesIO(file_content),
                                 download_name=filename,
                                 as_attachment=True)
            else:
                return jsonify({'message': 'Belge içeriği bulunamadı.'}), 404
        else:
            return jsonify({'message': 'Belge bulunamadı.'}), 404
    else:
        return jsonify({'message': 'Belge bulunamadı.'}), 404

if __name__ == '__main__':
    app.run(debug=True)
