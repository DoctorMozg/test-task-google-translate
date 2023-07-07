import uvicorn

from gtservice.app import create_application

app = create_application()

if __name__ == '__main__':
    uvicorn.run(app)
