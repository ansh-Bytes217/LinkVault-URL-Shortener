#URL Shortener System

This is a FastAPI application that uses MongoDB and Redis for data storage and caching. The application includes lifecycle management to handle the initialization and cleanup of these resources.

Features
FastAPI for building the web application
MongoDB for data storage
Redis for caching
Lifecycle management for resource initialization and cleanup
Requirements
Python 3.7+
FastAPI
Motor (Async MongoDB driver)
redis (Redis client with async support)

Installation
Clone the repository:
git clone https://github.com/ansh-Bytes217/LinkVault-URL-Shortener.git

cd url-shortener-system-design
Create a virtual environment and activate it:
python -m venv venv
source venv/bin/activate 

# On Windows use `venv\Scripts\activate`
Install the dependencies:
pip install -r requirements.txt
Configuration
Ensure you have MongoDB and Redis running on your machine or accessible from your application. Update the connection details in your application code if necessary. For running redis via docker container, make sure the latest version of docker is installed and run the following command -

docker run -d --name redis -p 6379:6379 redis
Running the Application independently
To run the FastAPI application, use the following command:

uvicorn fapp:app --port 5000
Github Actions CI pipeline setup
For CI pipeline, you need to add secrets to the repo after forking it.

Fork the repo and go to settings of the repository
Go to Security and then click on Actions
On the Secrets tab, click on button New repository secret and add the variable name and their values
Check the file ci.yml in .github folder and make sure your expected branch and docker image name and tag are set
Push a commit to code to run the CI pipeline
This will start the application in development mode with auto-reload enabled. Make sure mongodb local client is running or run it via docker as well like redis.

Application Structure
fapp.py
: Main application file containing the FastAPI app and lifecycle management.

Lifecycle Management
The application uses an asynchronous context manager to handle the lifecycle of MongoDB and Redis connections. The

lifecycle


function initializes the connections on startup and closes them on shutdown.

@asynccontextmanager

async def lifecycle(app: FastAPI):
    app.state.db
    app.state.collection = await initMongo()  # Initialize MongoDB
    
    app.state.redis = await async_get_redis_client()  # Initialize Redis
    
    yield  # Hand control to FastAPI
    
    await app.state.db.client.close()  # Close MongoDB connection
    
    await app.state.redis.close()  # Close Redis connection
    
Endpoints
GET /: Root endpoint that interacts with Redis.
POST /api/encode: Endpoint to shorten a URL. Expects a JSON body with a long_url field.
{
  "long_url": "https://example.com"
}

GET /{short_code}: Endpoint to redirect to the long url.
Since no DNS routes are setup, we use localhost routing with this short_code as the param

GET /health - Health endpoint of Redis and MongoDB connection

GET /docs - Swagger documentation of other list endpoints

Docker Compose for Entire Application

Run commands in sequence -

docker-compose build --no-cache
docker-compose up -d (detach mode)
Populate the MongoDB with data
Run file url_post_req.py to make post requests to populate the DB and check endpoints /api/urls for documents added.

Understand More
Refer to file Notes.md which includes the system design choices used to build this and ideal url shortener system in cluster setup.

Learning:

*Learnt development of Async applications in FastAPI

*Learnt pydantic validation along with best API practices

*Implemented MongoDB as NoSQL database and Redis as cache

*Built docker images for the service with best practices config and docker-compose for containerizing the application and database in same docker network

*Deployed application on kubernetes using YAML files with services as load balancer and ingress on minikube and used internal networking via FQDN urls and understood stateless application working

*Configured proper deployment, service, ingress, horizontal pod autoscaler for app along with ingress controller.

*Learnt StatefulSets for databases and other important kubernetes concepts like Persistent Volumes and Persistent Volume Claims

*Learnt best practices for configuration, uvicorn server and kubernetes

*Wrote tests for the app for local development via pytest and learnt fixtures, anyio package working and testing the core functionalities of the application

*Learnt system design principles of scalability for both application and database
