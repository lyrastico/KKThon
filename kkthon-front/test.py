import boto3

from dotenv import load_dotenv

import os

load_dotenv()

# Connexion automatique via les variables d'environnement

s3 = boto3.resource('s3')

bucket = s3.Bucket(os.getenv('S3_BUCKET_NAME'))

# Test : lister les dossiers bronze/silver/gold

for obj in bucket.objects.all():

    print(obj.key)
 