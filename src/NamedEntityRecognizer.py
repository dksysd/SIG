from pororo import Pororo


class NamedEntityRecognizer:
    def __init__(self):
        self.model = Pororo(task='ner', lang='ko')
        self.max_text_length = 512

    def analyze(self, text: str) -> list[tuple[str, str]]:
        if len(text) < self.max_text_length:
            return self.model(text)
        else:
            last_index = text[0:self.max_text_length].rfind(' ')
            if last_index == 0:
                last_index = text[0:self.max_text_length].rfind('\n')
                if last_index == 0:
                    last_index = self.max_text_length
            return self.analyze(text=text[0:last_index]) + self.analyze(text=text[last_index:])
