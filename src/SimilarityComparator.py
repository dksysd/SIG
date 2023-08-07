from gensim import models
from typing import Optional


class SimilarityComparator:
    def __init__(self, compare_model_vector: Optional[models] = None):
        """
        :param compare_model_vector: 유사도 비교에 사용할 모델의 벡터 (기본값 : fasttext/cc.ko.300.bin)
        """
        if compare_model_vector is None:
            self.compare_model_vector = models.fasttext.load_facebook_vectors('../model/fasttext/cc.ko.300.bin')
        else:
            self.compare_model_vector = compare_model_vector

    def get_similarity(self, word1: str, word2: str) -> float:
        """
        두 단어의 유사도 계산
        """
        return self.compare_model_vector.similarity(word1, word2)

    def is_similar(self, word1: str, word2: str, point: float) -> bool:
        """
        두 단어의 유사도가 기준점 초과인지 확인
        :param word1: 비교할 단어
        :param word2: 비교할 단어
        :param point: 기준점
        """
        return point < self.get_similarity(word1=word1, word2=word2)
