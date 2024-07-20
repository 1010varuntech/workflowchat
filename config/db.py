from pymongo import MongoClient

from dotenv import dotenv_values

config = dotenv_values(".env")

def connect_mongodb(app) :
    app.mongodb_client = MongoClient("mongodb+srv://varun:varun@cluster0.lsfxn8q.mongodb.net/")
    app.database = app.mongodb_client["appName=techStackStaging"]
    return "db connected sucessfully"