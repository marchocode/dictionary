from flask import Flask,render_template,abort
import pymongo

app = Flask(__name__)

client = pymongo.MongoClient("mongodb://root:root@127.0.0.1:27017")
db = client["test"]
collection = db["dictionary"]

@app.route('/dictionary/english/<word>', methods=['GET'])
def hello(word=None):

    data = collection.find_one({"_id": word})
    
    if data is None:
        abort(404)
    
    app.logger.info(f'receive a word {word}')
    return render_template('index.html', data=data)