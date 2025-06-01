import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from pydantic_settings import BaseSettings
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import uvicorn
from pydantic import BaseModel, HttpUrl
from random import randint
from typing import Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import redis.asyncio as redis
from fastapi.responses import JSONResponse
import hashlib

'''
References for implementation in FastAPI: 

https://fastapi.tiangolo.com/advanced/events/#lifespan
https://docs.pydantic.dev/latest/concepts/pydantic_settings/

'''

load_dotenv()


class URLRequest(BaseModel):
    long_url: HttpUrl

class URLResponse(BaseModel):
    short_url: Optional[str]=None   
    long_url: str
    error_message:Optional[str]=None


async def async_get_redis_client():
    try:
        client = await redis.Redis.from_url(settings.REDIS_LOCAL_URL if settings.LOCAL else settings.REDIS_K8S_URL)
        # Test the connection
        await client.ping()
        logger.info("Connected to Redis!")
        return client
    except redis.RedisError as e:
        logger.info(f"Redis connection error: {e}")

async def initMongo()-> Tuple[AsyncIOMotorDatabase, AsyncIOMotorCollection]:
    try:
        client = AsyncIOMotorClient(settings.MONGODB_LOCAL_URL) if settings.LOCAL else AsyncIOMotorClient(settings.MONGODB_CONTAINER_URL)
        db = client[settings.DATABASE_NAME]
        collection = db[settings.COLLECTION_NAME]
        
        # verify connection
        await client.admin.command('ping')
        logger.info("Connected to mongDB")
        return db, collection
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {str(e)}")
        return None, None


@asynccontextmanager
async def lifecycle(app: FastAPI):
    app.state.db, app.state.collection = await initMongo() # code before yield runs on startup
    app.state.redis = await async_get_redis_client()
    yield # give control to fastapi (fastapi handles requests while the app is running)
    await app.state.db.client.close() # code after yield runs on shutdown (of fastapi server)
    await app.state.redis.close()


app = FastAPI(lifespan=lifecycle)


# Configuration management
class Settings(BaseSettings):
    MONGODB_LOCAL_URL: str = "mongodb://localhost:27017"
    MONGODB_CONTAINER_URL: str = "mongodb://mongo:27017"
    MONGODB_K8S_URL: str = "mongo.default.svc.cluster.local:27017"
    REDIS_K8S_URL:str = "redis://redis.default.svc.cluster.local:6379"
    REDIS_LOCAL_HOST: str = "localhost"
    REDIS_CONTAINER_HOST: str = "redis"
    REDIS_LOCAL_URL:str = "redis://localhost:6379"
    # REDIS_PORT: int = 6379 # some problem with int passing in k8s where it considers it as string of tcp port with internal IP
    DATABASE_NAME: str = "url_shortener_db"
    LOCAL_APP_HOST: str = "localhost"
    CONTAINER_APP_HOST: str = "0.0.0.0"
    LOCAL: bool = True
    COLLECTION_NAME: str = "url_collection"
    ALLOWED_ORIGINS: list = [
        "http://localhost:5000",
        "http://localhost:8000",
    ]
    class Config:
        # Allow the environment variables to override the settings in the class
        env_file = ".env"
        env_file_encoding = "utf-8"

print(Settings())    
settings = Settings() 

print(os.getenv("LOCAL", "True"))
print(os)
settings.LOCAL = os.getenv("LOCAL", "True").lower() == "true" 
print(settings.LOCAL)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


    
# allow cors for these below urls
origins = [
    "http://localhost:5000",
    "http://localhost:8000",
    # Add more origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    

@app.get("/")
async def root():
    return JSONResponse(content={"message": "Home page"}, status_code=200)

@app.get("/health")
async def health():
    redis_status = "OK"
    mongo_status = "OK"
    try:
        await app.state.db.command("ping")
    except Exception as e:
        mongo_status=str(e)
    try:
        await app.state.redis.ping()
    except Exception as e:
        redis_status=str(e)
    
    return JSONResponse(status_code=200, content={"status": "OK", "MongoDB Connection": mongo_status, "Redis Connection": redis_status})


def shorten_url(original_url):
    hash_object = hashlib.sha256(original_url.encode())
    hashed_url = hash_object.hexdigest()
    short_hash = hashed_url[:8] 
    
    short_url = f"http://localhost:5000/{short_hash}"
    
    return short_url

@app.post("/api/encode", response_model=URLResponse)
async def encode(request: URLRequest):
    if app.state.db is None or app.state.collection is None:
        return URLResponse(long_url=request.long_url, error_message="Cannot establish connection to MongoDB database")
    else:
        long_url = str(request.long_url)
        logger.info(f"Received long url: {long_url}")
        query = {"long_url": long_url}
        try:
            count  = await app.state.collection.count_documents(query)
            # count=0 # uncomment to check collision match
            if count>0:
                logger.info(f"Long url already exists in DB")
                document = await app.state.collection.find_one(query)
                short_url = document["short_url"]
                return URLResponse(short_url=short_url, long_url=long_url)
            else:
                short_url = ""
                isValidShortUrl = False
                max_retries=5
                counter=1
                new_url = long_url
                while not isValidShortUrl and max_retries>0:
                    short_url = shorten_url(new_url)
                    check_query = {"short_url": short_url}
                    count = await app.state.collection.count_documents(check_query)
                    if count==0:
                        isValidShortUrl = True
                    else:
                        logger.info(f"Short url already exists for {long_url}. Generating a new one...")
                    
                    new_url = new_url + f"_{counter}" # modify url for collision
                    counter+=1
                    max_retries-=1
                
                if max_retries==0:
                    raise Exception("Could not generate a unique short url after 10 retries")
                # insert a new document
                new_doc = {}
                new_doc["long_url"] = long_url
                new_doc["short_url"] = short_url
                
                await app.state.collection.insert_one(new_doc) # added to the db
                logger.info(f'Document inserted of long url {long_url}')
                return URLResponse(short_url=short_url, long_url=long_url)
        except Exception as e:
            return URLResponse(long_url=long_url, error_message=str(e))

@app.get("/{short_code}")
async def decode(short_code: str):
    short_url = f"http://localhost:5000/{short_code}"
    query = {"short_url": f"http://localhost:5000/{short_code}"}
    try:
        # add redis check here
        long_url = await app.state.redis.get(short_url)
        if long_url is not None:
            # redis problem with bytes when you access the cached url, it redirects to wrong url which needs decoding first
            long_url = long_url.decode("utf-8") # convert bytes to string as after cache the url is stored as bytes like b'https://minikube.sigs.k8s.io/docs/handbook/accessing/'
            return RedirectResponse(url=long_url)
        else:
            logger.info("cache miss")
            document = await app.state.collection.find_one(query)
            if document is not None:
                long_url = document["long_url"]
                await app.state.redis.set(short_url, long_url) # add key-value pair to redis
                return RedirectResponse(url=long_url)
            else:
                return JSONResponse(content={"message": "No such short url found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/urls")
async def list_urls():
    """
    Retrieve all documents from the MongoDB collection.

    Returns:
        JSONResponse: A JSON response containing the documents or an error message.
    """
    try:
        cursor = app.state.collection.find({}, {"_id": 0})
        documents = await cursor.to_list(length=1000)
        if documents == []:
            return JSONResponse(content={"message": "Empty collection"}, status_code=200)
        elif documents is None:
            return JSONResponse(content={"error": "No documents found"}, status_code=404)
        else:
            return JSONResponse(content={"documents": documents}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/redis/list")
async def get_all_redis_pairs(batch_size: int = 500):
    """
    Retrieve all key-value pairs from Redis in batches.

    Args:
        batch_size (int): The number of keys to retrieve in each batch. Default is 500.

    Returns:
        dict: A dictionary containing all key-value pairs from Redis.
    """
    pairs = {}
    try:
        async for key in app.state.redis.scan_iter(match="*", count=batch_size):
            value = await app.state.redis.get(key)
            pairs[key] = value
        return pairs
    except redis.RedisError as e:
        return {"Redis error": str(e)}
    except Exception as e:
        return {"error": str(e)}
    


# 0.0.0.0 makes app accessible to any device on the network, otherwise 127.0.0.1 restricts to localhost
if __name__ == "__main__":
    host = settings.LOCAL_APP_HOST if settings.LOCAL else settings.CONTAINER_APP_HOST
    # put 0.0.0.0 for docker
    uvicorn.run("fapp:app", host=host, port=5000, reload=True) # reload=True for auto-reload on code changes
    # passed "fapp:app" as reload=True expects this format and "fapp" is the name of the file/module
