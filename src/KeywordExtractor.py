from typing import List, Optional

from keybert import KeyBERT
from transformers import BertModel


class KeywordList:
    class Keyword:
        def __init__(self, keyword: str, score: float):
            self._keyword = None
            self._score = None
            self.set_keyword(keyword)
            self.set_score(score)

        def set_keyword(self, keyword: str):
            self._keyword = keyword

        def get_keyword(self) -> str:
            return self._keyword

        def set_score(self, score: float):
            self._score = score

        def get_score(self) -> float:
            return self._score

    def __init__(self):
        self._keyword_with_score_list: List[KeywordList.Keyword] = []

    def get_keyword(self, index: int) -> Keyword:
        """
        index번째 키워드 반환
        :return: (key : 'keyword', 'score')
        """
        return self._keyword_with_score_list[index]

    def get_keywords(self) -> List[Keyword]:
        """
        모든 키워드 반환
        """
        return self._keyword_with_score_list

    def add_keyword(self, keyword: str, score: float):
        """
        키워드 추가.
        만약 존재하는 키워드일 경우, 새로운 가중치를 합한 값이 저장됨.
        """
        index = self.find_index(keyword=keyword)
        if index is None:
            self._add_keyword(keyword=keyword, score=score)
        else:
            ori_keyword = self.get_keyword(index)
            self._add_keyword(keyword=keyword, score=(score + ori_keyword.get_score()))

    def _add_keyword(self, keyword: str, score: float):
        """
        keyword와 score를 저장
        """
        self._keyword_with_score_list.append(self.Keyword(keyword=keyword, score=score))

    def find_index(self, keyword: str) -> Optional[int]:
        """
        키워드가 저장된 index 반환
        """
        for index in range(len(self._keyword_with_score_list)):
            if keyword == self._keyword_with_score_list[index].get_keyword():
                return index
        return None

    def contain(self, keyword: str) -> bool:
        """
        키워드가 포함되어 있는지 확인
        """
        return 0 <= self.find_index(keyword=keyword)

    def empty(self) -> bool:
        """
        저장되어 있는 것이 있는지 확인
        """
        return 0 < len(self)

    def __len__(self) -> int:
        """
        :return: 저장되어 있는 키워드 수
        """
        return len(self._keyword_with_score_list)


class KeywordExtractor:
    def __init__(self, bert_model_name: str = 'skt/kobert-base-v1'):
        """
        :param bert_model_name: huggingface.co의 모델 저장소에 있는 모델 이름
        """
        bert_model = BertModel.from_pretrained(bert_model_name)
        self.keyword_model = KeyBERT(bert_model)

    def get_keywords(self, text: str, top_n: int = 10, ngram_range: tuple[int, int] = (1, 3)) -> KeywordList:
        """
        문장에서 키워드 추출
        :param text:분석할 문장
        :param top_n:가중치가 높은 순서대로 n개 추출
        :param ngram_range:키워드 ngram 값 범위 
        :return: 단어와 가중치가 포함된 배열
        """
        result_keyword_list = KeywordList()
        for keyword, score in self.keyword_model.extract_keywords(text, top_n=top_n, keyphrase_ngram_range=ngram_range):
            result_keyword_list.add_keyword(keyword=keyword, score=score)
        return result_keyword_list
