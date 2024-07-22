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
    # Mevcut versiyonları kontrol et
    existing_versions = list(documents_collection.find({'filename': {'$regex': f'^{filename}(\\_v[0-9]+)?$'}}))
    if not existing_versions:
        return filename  # İlk versiyon

    version_numbers = []
    for doc in existing_versions:
        # Dosya isimlerindeki versiyon numaralarını ayıkla
        parts = doc['filename'].rsplit('_v', 1)
        if len(parts) == 2 and parts[1].isdigit():
            version_numbers.append(int(parts[1]))

    if version_numbers:
        new_version = max(version_numbers) + 1
    else:
        new_version = 1

    return f"{filename}_v{new_version}"

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

    # HTML şablonunu render et
    return render_template('dosyalar.html', documents=documents)

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
