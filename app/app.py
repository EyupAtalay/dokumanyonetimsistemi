from bson import ObjectId
from flask import Flask, render_template, request, jsonify, send_file, session
from pymongo import MongoClient
import hashlib
import io
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'eyupatalay'

# MongoDB bağlantısı ve koleksiyon tanımlaması
client = MongoClient('mongodb://localhost:27017/')
db = client['dokuman_versiyon']
documents_collection = db['dokuman']
users_collection = db['users']

# Ana sayfa, dosya yükleme formu
@app.route('/', methods=['GET'])
def index():

    return render_template('login.html')

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
    if 'user_id' not in session:
        return render_template('login.html', message='Oturum açmanız gerekiyor.')

    file = request.files['file']
    file_content = file.read()

    # Dosyanın içeriğini SHA-256 ile hashleme
    file_hash = hashlib.sha256(file_content).hexdigest()

    # Veritabanında aynı hash değerine sahip belgeyi kontrol et
    existing_document = documents_collection.find_one({'hash': file_hash, 'user_id': session['user_id']})

    if existing_document:
        return render_template('index.html', message='Bu belge zaten var.')
    
    else:
        # Aynı isimdeki dosyalar için versiyon belirleme
        new_filename = get_new_versioned_filename(file.filename)

        # Yeni belgeyi veritabanına ekle
        document_data = {
            'filename': new_filename,
            'content': file_content,
            'hash': file_hash,
            'user_id': session['user_id']
        }
        documents_collection.insert_one(document_data)
        
        return render_template('index.html', message='Dosya başarıyla yüklendi.')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        
        # Kullanıcıyı veritabanından bulma
        user = users_collection.find_one({'name': name})

        if user and check_password_hash(user['password'], password):
            # Kullanıcı doğrulandı, oturum aç
            session['user_id'] = str(user['_id'])
            return render_template('index.html')
    
    return render_template('login.html', message='Kullanıcı adı veya şifre yanlış')
    

# Yüklenmiş belgeleri listeleme
@app.route('/dosyalar', methods=['GET', 'POST'])
def list_documents():
    if 'user_id' not in session:
        return render_template('login.html', message='Oturum açmanız gerekiyor.')
    
    documents = list(documents_collection.find({'user_id': session['user_id']}, {'_id': 0}))  # _id alanını hariç tut
    return render_template('dosyalar.html', documents=documents)

@app.route('/kayıtol', methods=['GET', 'POST'])
def register():
    registration_date = datetime.now()
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        
        
        # Şifreyi hash'leyerek güvenli hale getirme
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Kullanıcı verilerini MongoDB'ye kaydetme
        users_collection.insert_one({'name': name, 'password': hashed_password,'tarih': registration_date})
        
        return render_template('kayıt.html',message="Başarıyla Kayıt Olundu")
    return render_template('kayıt.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return render_template('login.html', message='Başarıyla çıkış yaptınız.')

# Belge indirme endpoint'i
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    if 'user_id' not in session:
        return render_template('login.html', message='Oturum açmanız gerekiyor.')

    document = documents_collection.find_one({'filename': filename, 'user_id': session['user_id']})
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
    



@app.route('/anasayfa')
def anasayfa():
    return render_template('index.html')


@app.route('/profil')
def profile():
    if 'user_id' not in session:
        return render_template('login.html', message='Oturum açmanız gerekiyor.')

    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    if user:
        return render_template('profil.html', user=user)
    else:
        return jsonify({'message': 'Kullanıcı bulunamadı.'}), 404


if __name__ == '__main__':
    app.run(debug=True)
