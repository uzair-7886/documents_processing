# celery_config.py
# from flask import Flask, current_app
# from celery import Celery


# def make_celery(app):
#     celery = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'], broker=app.config['CELERY_BROKER_URL'])
#     celery.conf.update(app.config)

#     class ContextTask(celery.Task):
#         def __call__(self, *args, **kwargs):
#             with app.app_context():
#                 return celery.Task.__call__(self, *args, **kwargs)

#     celery.Task = ContextTask
#     return celery