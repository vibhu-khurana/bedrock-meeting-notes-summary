import boto3
import botocore.config
import json
import base64
from datetime import datetime
from email import message_from_bytes


def extract_text_from_multipart(data):
    msg = message_from_bytes(data)

    text_content = ''

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                text_content += part.get_payload(decode=True).decode('utf-8') + "\n"

    else:
        if msg.get_content_type() == "text/plain":
            text_content = msg.get_payload(decode=True).decode('utf-8')

    return text_content.strip() if text_content else None


def generate_summary_from_bedrock(content:str) ->str:

    # Create a Bedrock Runtime client in the AWS Region of your choice.
    client = boto3.client("bedrock-runtime", region_name="us-east-1")

    # Set the model ID, e.g., Claude 3 Haiku.
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    
    prompt = f"""Human: Summarize the following meeting notes: {content}
    Assistant:"""

    # Format the request payload using the model's native structure.
    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "temperature": 0.5,
        "messages": [
            {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
            }
        ],
    }

    # Convert the native request to JSON.
    request = json.dumps(native_request)

    try:
        response = client.invoke_model(modelId=model_id, body=request)
        response_content = response["body"].read().decode("utf-8")
        response_data = json.loads(response_content)
        response_data = json.loads(response_content)
        summary = response_data["content"][0]["text"].strip()
        return summary

    except Exception as e:
        print(f"Error generating the summary: {e}")
        return ""

def save_summary_to_s3_bucket(summary, s3_bucket, s3_key):

    s3 = boto3.client('s3')
    print(f's3 {s3}')

    try:
        s3.put_object(Bucket = s3_bucket, Key = s3_key, Body = summary)
        print("Summary saved to s3")

    except Exception as e:
        print("Error when saving the summary to s3")


def lambda_handler(event,context):

    decoded_body = base64.b64decode(event['body'])

    text_content = extract_text_from_multipart(decoded_body)

    if not text_content:
        return {
            'statusCode':400,
            'body':json.dumps("Failed to extract content")
        }


    summary = generate_summary_from_bedrock(text_content)

    if summary:
        current_time = datetime.now().strftime('%H%M%S') #UTC TIME, NOT NECCESSARILY YOUR TIMEZONE
        s3_key = f'summary-output/{current_time}.txt'
        s3_bucket = 'bedrock-meeting-sum-bucket'

        save_summary_to_s3_bucket(summary, s3_bucket, s3_key)

    else:
        print("No summary was generated")


    return {
        'statusCode':200,
        'body':json.dumps("Summary generation finished")
    }

    