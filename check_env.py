import os
from dotenv import load_dotenv

load_dotenv()

print("✅ USE_S3:", os.getenv("USE_S3"))
print("✅ DEBUG:", os.getenv("DEBUG"))
print("✅ AWS_BUCKET:", os.getenv("AWS_STORAGE_BUCKET_NAME"))
