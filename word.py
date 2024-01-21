import pymongo
import requests
import json
import re
from bs4 import BeautifulSoup
from bs4.element import Tag,NavigableString
from urllib import parse

myclient = pymongo.MongoClient("mongodb://root:root@127.0.0.1:27017")
mydb = myclient["test"]

mycol = mydb["dictionary"]
voice_uk = mydb["voice_uk"]
voice_us = mydb["voice_us"]

headler={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

domain="https://dictionary.cambridge.org/"


class CambridgeDictionary:
    
    def __init__(self,word) -> None:
        
        self.word = word
        self.dictionary = None
        
        self.object = {
            "_id": word,
            "url": None,
            "voice": {},
            "bodies": []
        }
        
        self.voice = None

    def url_formater(self, word) -> str:
        return f"https://dictionary.cambridge.org/dictionary/english/{word}"
    
    def request_dictionary(self) -> Tag:
        
        url = self.url_formater(self.word)
        response = requests.get(url,headers=headler, allow_redirects=False)
        
        if 302 == response.status_code:
            location = response.headers['Location']
            word = re.search(r'/([a-z]+)\?', location).group(1)
            self.word = word
            self.object['_id'] = word
            
            url = self.url_formater(self.word)
            response = requests.get(url,headers=headler)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        self.dictionary = soup.select_one('div.pr.dictionary[data-id="cald4"]')
        
        self.object['url'] = url
        
        return self.dictionary
    
    def handler_voice(self):
        
        if self.dictionary is None:
            return None
        
        audio1 = self.dictionary.select_one('audio#audio1')
        audio2 = self.dictionary.select_one('audio#audio2')

        audio1_url = audio1.select_one('source[type="audio/mpeg"]')['src']
        audio2_url = audio2.select_one('source[type="audio/mpeg"]')['src']

        uk = parse.urljoin(domain,audio1_url)
        us = parse.urljoin(domain,audio2_url)
        
        self.object['voice']['uk'] = uk
        self.object['voice']['us'] = us
        
        uk_response = requests.get(uk,headers=headler,stream=True)
        us_response = requests.get(us,headers=headler,stream=True)
        
        self.voice = (uk_response.raw.read(),us_response.raw.read())
    
    def handler_pos(self,body) -> str:
        
        pos = body.select_one('span.pos.dpos')
        
        if pos is None:
            return None
            
        return pos.text
    
    def handler(self):
        
        bodies = self.object['bodies']
        
        for body in self.dictionary.select('div.pr.entry-body__el'):
            
            define = self.handler_body(body)
            # define pos
            define['pos'] = self.handler_pos(body)
            
            bodies.append(define)

        return bodies
    
    def handler_body(self,item) -> dict:
        
        body = {};        
        body['list'] = []
        
        for dsense in item.select('div.pr.dsense'):

            obj={}

            obj['guide']=self.handler_guide_word(dsense)
            
            clas = dsense.select_one('span.epp-xref.dxref')
            if clas:
                obj['degree']=clas.text
            
            ddef = dsense.select_one('div.def.ddef_d.db')
            
            obj['define']=ddef.text
            obj['examples']=self.handler_examples(dsense)

            
            body['list'].append(obj)
        
        return body
    
    def handler_guide_word(self,item) -> str:
        
        ob = item.select_one('span.guideword.dsense_gw')
        
        if ob is None:
            return None
        return ob.span.text
    
    def handler_examples(self,item) -> list:
        
        li = []
        examples = item.select('span.eg.deg')
        
        for example in examples:
            li.append(example.text)
        
        return li
        
    def start(self):
        
        self.request_dictionary()
        
        self.handler_voice()
        self.handler()
        
        with open('output.json','w') as f:
            f.write(json.dumps(self.object))
    
    def write_db(self):
        # write a db
        mycol.insert_one(self.object)
        
        voice_uk.insert_one({'_id': self.word,"data": self.voice[0]})
        voice_us.insert_one({'_id': self.word,"data": self.voice[1]})        
    
cambridge = CambridgeDictionary('cat')

cambridge.start()
cambridge.write_db()