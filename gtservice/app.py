import logging
import time

from fastapi import FastAPI, Request

from gtservice import settings

logger = logging.getLogger(__name__)


def prepare_logger():
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format='%(asctime)s %(name)s %(levelname)s: %(message)s'
    )


def init_middleware(app: FastAPI):
    @app.middleware('http')
    async def log_request(request: Request, call_next):
        start = time.monotonic()
        try:
            logger.info('Request has started')
            return await call_next(request)
        finally:
            logger.info(f'Request has ended. Elapsed time: {time.monotonic() - start}')


def init_routers(app: FastAPI):
    from gtservice.api.translations import router as words_router
    app.include_router(router=words_router)


def create_application():
    prepare_logger()

    app = FastAPI(title="Google Translate Service")

    init_middleware(app)
    init_routers(app)

    return app
