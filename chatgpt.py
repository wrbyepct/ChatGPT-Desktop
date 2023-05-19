import openai 

class ChatGPT:
    def __init__(self, api_key):
        self.openai = openai
        self.openai.api_key = api_key
        self.messages = []
    
    def send_request(self, prompt, max_tokens=4096, temperature=1.0):
        try:
            self.messages.append({'role': 'user', 'content': prompt})
            response = self.openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                max_tokens=max_tokens,
                temperature=temperature,
                messages=self.messages
            )
            self.messages.append({'role': 'assistant', 'content': response.choice[0].message.content})
            return {'usage': response.usage.total_tokens, 'content': response.choice[0].message.content}
        except Exception as e:
            return {'error': e}