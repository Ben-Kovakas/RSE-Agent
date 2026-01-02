from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5-nano",
    input = "Say 'Hello, RSE Agent!' and nothing else."
)

print(response.output_text)