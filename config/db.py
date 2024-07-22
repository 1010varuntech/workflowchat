from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def connect_mongodb(app) :
    app.mongodb_client = MongoClient(os.getenv("DB_URI"))
    app.database = app.mongodb_client[os.getenv("DB_NAME")]
    return "db connected sucessfully"