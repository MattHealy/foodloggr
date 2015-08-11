from uuid import uuid4
import boto
import os.path
from flask import current_app as app
from werkzeug.utils import secure_filename
from .. import celery

def local_upload(source_file):
    source_filename = secure_filename(source_file.data.filename)
    source_extension = os.path.splitext(source_filename)[1]
    destination_filename = uuid4().hex + source_extension
    source_file.data.save(os.path.join(app.config['UPLOAD_FOLDER'], destination_filename))

    s3_upload.delay(destination_filename)

    return destination_filename

@celery.task
def s3_upload(source_filename, acl='public-read'):
    """ Uploads Local File Object to Amazon S3

        Expects following app.config attributes to be set:
            S3_KEY              :   S3 API Key
            S3_SECRET           :   S3 Secret Key
            S3_BUCKET           :   What bucket to upload to
            S3_UPLOAD_DIRECTORY :   Which S3 Directory.

        The default sets the access rights on the uploaded file to
        public-read.  It also generates a unique filename via
        the uuid4 function combined with the file extension from
        the source file.
    """

    # Connect to S3 and upload file.
    conn = boto.connect_s3(app.config["S3_KEY"], app.config["S3_SECRET"])
    b = conn.get_bucket(app.config["S3_BUCKET"])

    sml = b.new_key("/".join([app.config["S3_UPLOAD_DIRECTORY"], source_filename]))
    sml.set_contents_from_filename(os.path.join(app.config['UPLOAD_FOLDER'], source_filename))
    sml.set_acl(acl)

    os.unlink(os.path.join(app.config['UPLOAD_FOLDER'], source_filename))

