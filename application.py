import os
import psycopg2
import tweepy
import base64
import hashlib
import hmac
import json

from dog import dog, pic_file
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
from sqlalchemy.sql import func
from sqlalchemy import Identity
from time import sleep


#env variables
C_KEY = os.environ['consumer_key']
C_SECRET = os.environ['consumer_secret']
A_TOKEN = os.environ['access_token']
A_TOKEN_SECRET = os.environ['access_token_secret']
BOT_ID = os.environ['BOT_ID']
DATABASE_URL = os.environ['DB_URL']
WEB_CONCURRENCY = os.environ['WEB_CONCURRENCY']

# set config values
class Config(object):
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "America/New_York"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = DATABASE_URL


#name, init
app = Flask(__name__)
app.config.from_object(Config())

scheduler = APScheduler()
scheduler.init_app(app)

db = SQLAlchemy(app)
connection = psycopg2.connect(DATABASE_URL, sslmode='require')
db.create_all()


# DB tables
class Followers(db.Model):
    id = db.Column(db.String(80), primary_key = True)
    handle = db.Column(db.String(80), nullable = False)
    timestamp = db.Column(db.TIMESTAMP, server_default=func.now())

    def __init__(self, id, handle, timestamp=None):
        self.id = id
        self.handle = handle
        self.timestamp = timestamp

class Breed(db.Model):
    row_id = db.Column(db.Integer, Identity(always=True, start=1, increment=1), primary_key = True)
    follower_id = db.Column(db.String(80), db.ForeignKey('followers.id'))
    chosen_breed = db.Column(db.String(80), nullable = False)

    def __init__(self, follower_id, chosen_breed, row_id=None):
        self.row_id = row_id
        self.follower_id = follower_id
        self.chosen_breed = chosen_breed

# Twitter auth
auth = tweepy.OAuthHandler(C_KEY, C_SECRET)
auth.set_access_token(A_TOKEN, A_TOKEN_SECRET)
api = tweepy.API(auth)

@app.route('/')
def index():
    return f"<h3>Welcome to dogbot!</h3>"

@app.route('/webhooks/twitter', methods=['GET', 'POST'])
def webhooks():
    if request.method=='GET':
        consumer_secret_bytes = bytes(C_SECRET,'utf-8') 
        message = bytes(request.args.get('crc_token'),'utf-8')

        sha256_hash_digest = hmac.new(consumer_secret_bytes, message, digestmod=hashlib.sha256).digest()
        response={
            'response_token':'sha256='+base64.b64encode(sha256_hash_digest).decode('utf-8')
        }
        return json.dumps(response)

    elif request.method=='POST':
        r = request.get_json()
        event_parse(r)
        return print(r)

#see which webhook it is
def event_parse(r):
    if 'follow_events' in r:
        return new_followers(r)
    #elif r.
    elif 'direct_message_events' in r:
        if r['direct_message_events'][0]['message_create']['sender_id'] != BOT_ID:
            #if its a quickreply
            tw_follower_id = r['direct_message_events'][0]['message_create']['sender_id']
            if 'quick_reply_response' in r['direct_message_events'][0]['message_create']['message_data']:
                return quick_reply_handler(r,tw_follower_id)
            else: 
                return dm_handler(r,tw_follower_id)

def new_followers(r):
    tw_follower_id = r['follow_events'][0]['source']['id']
    tw_follower_handle = r['follow_events'][0]['source']['screen_name']
    if Followers.query.filter_by(id = tw_follower_id).all() == []:
        # follower is new. add them to db
        new = Followers(id = tw_follower_id, handle = tw_follower_handle)
        db.session.add(new)
        db.session.commit()
        intro_dm(tw_follower_id)
    #if follower is not new and just refollowed, but they already have a breed
    elif Breed.query.filter_by(follower_id = tw_follower_id).all() != []:
        breed = Breed.query.filter_by(follower_id = tw_follower_id).first()
        if breed.chosen_breed != 'all':
            text = f"Welcome back! I'll start tweeting you {breed.chosen_breed} again."
        else:
            text = f"Welcome back! I'll start tweeting you dogs again."
        api.send_direct_message(recipient_id=tw_follower_id, text=text)
        sleep(1.5)
        api.send_direct_message(recipient_id=tw_follower_id, text="If you want to change breeds, just dm me a different breed!")
    else:
    #else, they dont' have a breed. you can prompt them again in the new follower flow.
        return False
    return

def intro_dm(tw_follower_id):    
    text1 = ("Hi! i'm DogBot. I tweet you dogs every monday morning.")
    text2 = ("Do you want to see your favorite breed, or all dogs? Select an option below.")
    text2_options = [
        {
            'label': 'all the dogs',
            'metadata': 'all'
        },
        {
            'label': 'just my fav',
            'metadata': 'pick'
        }
    ]
    api.send_direct_message(tw_follower_id,text1)
    sleep(2)
    return api.send_direct_message(recipient_id=tw_follower_id, text=text2, quick_reply_options=text2_options)

def quick_reply_handler(r,tw_follower_id):
    x = r['direct_message_events'][0]['message_create']['message_data']['quick_reply_response']['metadata']
    if x == 'all':
        api.send_direct_message(tw_follower_id, text="You get all the dogs! First doggy comes to your timeline on monday :)")
        sleep(1)
        return api.send_direct_message(tw_follower_id, text='If you ever want to change dog breeds, just send me dm with a different breed.')
    elif x == 'pick':
        api.send_direct_message(tw_follower_id, text="Understood, of course. What breed of dog do you want to see?")
        sleep(1)
        return 
    else:
        return dm_handler(r,tw_follower_id)

def dm_handler(r, tw_follower_id):
    breed = r['direct_message_events'][0]['message_create']['message_data']['text']
    dog_pick = dog(breed)
    print(dog_pick)
    if len(dog_pick) > 1:
        optionslist = []
        for dogs in dog_pick:
            options = {}
            options['label'] = dogs
            options['metadata'] = dogs
            optionslist.append(options)
        print(optionslist) 
        api.send_direct_message(recipient_id=tw_follower_id, text="OOf. Dogbot isn't totally sure what type of dog you mean.")
        sleep(1)
        api.send_direct_message(recipient_id=tw_follower_id, text="I found the following dogs that might be what you're looking for. Choose one, or you can type another breed!", quick_reply_options=optionslist)
        sleep(1)
        return
    dog_pick = str(dog_pick).replace('{','').replace('"','').replace('}','').replace('[','').replace(']','').replace("'","")
    new = Breed(follower_id = tw_follower_id, chosen_breed=dog_pick)
    if Breed.query.filter_by(follower_id = tw_follower_id).all() != []:
        old = Breed.query.filter_by(follower_id = tw_follower_id).all()
        for row in old:
            db.session.delete(row)
            db.session.commit()
    db.session.add(new)
    db.session.commit()
    if 'all' not in dog_pick:
        text = "Great! you'll get " + breed + "s!  If you ever want a different breed, just send me a dm with that new breed."
    else:
        text = "You get all the dogs. If you want a different breed, just type the name of that breed."
        new = 'all'
        db.session.add(new)
        db.session.commit()
    api.send_direct_message(tw_follower_id,text)
    sleep(1)
    return

@scheduler.task(trigger='cron', id='tweet', timezone ='America/New_York', day_of_week='mon', hour='10', minute = '55')
def tweet_followers():
    api_followers = api.get_follower_ids(user_id = BOT_ID, stringify_ids = True)
    db_followers = Followers.query.all()
    for follow in db_followers:
        if follow.id not in api_followers:
            follower_breed = Breed.query.filter_by(follower_id = follow.id).all()
            for row in follower_breed:
                db.session.delete(row)
                db.session.commit()
            db.session.delete(follow)
            db.session.commit()
        else:
            handle = follow.handle
            breed = Breed.query.filter_by(follower_id = follow.id).first()
            if breed.chosen_breed != '':
                pic = pic_file(breed.chosen_breed)
                try:
                    media = api.simple_upload(filename=pic, media_category='tweet_image')
                except tweepy.TweepyException as e:
                    print(e.message)

                media_id = [media.media_id]
                text = ('@'+ handle + ' another monday, another good dog!')
                sleep(1)
                try:
                    api.update_status(status=text, media_ids=media_id)
                except tweepy.TweepyException as e:
                    print(e.message)
                else:
                    if pic:
                        os.remove(pic)

scheduler.start()

if __name__ == "__main__":    
    app.run()
