from functools import partial
from typing import List, Dict, Tuple, Union, Iterable

import numpy as np
import pandas as pd
from kiwipiepy import Kiwi, Token


class MorphemeAnalyzer:
    def __init__(self, is_typos: bool = False, num_workers: int = 0,
                 unit_scale: bool = True, dynamic_ncols: bool = True):
        """
        :param is_typos: 문장 교정 여부 (활성화 할 경우 초가화 시에 약 5~10초 정도의 시간이 추가로 소요되며, 문장 당 처리 시간은 2배 정도 늘어남)
        :param num_workers: 형태소 분석에 사용할 스레드 수
        :param unit_scale: 진행 상황 출력 시, 반복 횟수 단위 자동 축소 및 확대 (성능에 영향을 미칠 가능성 있음)
        :param dynamic_ncols: 진행 상황 출력 시, 가로 폭에 따라 능동적으로 수정 (성능에 영향을 미칠 가능성 있음)
        """
        typos = 'basic' if is_typos else None
        self._kiwi = Kiwi(typos=typos, num_workers=num_workers)
        self.add_user_word(word='안녕하세요', tag='VA', score=1)

    def add_user_word(self, word: str, tag: str = 'NNP', score: float = 0.) -> None:
        """
        형태소 분석기에 사용자 정의 사전 추가
        :param word: 추가할 단어
        :param tag: 형태소 태그 (형태소 태그 표 : https://bab2min.github.io/kiwipiepy/v0.15.2/kr/#_9)
        :param score: 추가할 단어에 대한 가중치
        """
        self._kiwi.add_user_word(word=word, tag=tag, score=score)

    def add_user_words(self, word_list: List[Dict[str, str]]) -> None:
        """
        형태소 분석기에 사용자 정의 사전 여러개 추가
        :param word_list: 사용자 정의 사전 배열 (score는 생략될 수 있음)
        (예시 : [{'word':'사과', 'tag':'NNG','score':'0'}, {'word':'바나나', 'tag':'NNG'}])
        """
        for inner in word_list:
            word = inner.get('word')
            tag = inner.get('tag')
            score = inner.get('score')

            if score is None:
                self.add_user_word(word, tag)
            else:
                self.add_user_word(word, tag, float(score))

    def join(self, morphs: Iterable[Union[Token, Tuple[str, str], Tuple[str, str, bool]]]) -> str:
        """
        형태소 분석 결과 복원
        :param morphs: 형태소 분석 결과
        :return: 복원 결과
        """
        return self._kiwi.join(morphs=morphs)

    def tokenize(self, text: str) -> Union[
        List[Token], Iterable[List[Token]], List[List[Token]], Iterable[List[List[Token]]]]:
        """
        문장 토큰화
        :param text: 분석할 문장
        :return: 분석 결과
        """
        return self._kiwi.tokenize(text=text)

    def get_nouns(self, text: str) -> List[str]:
        """
        입력에 대한 명사들 추출. 여기서 명사는 NNG(일반 명사), NNP(고유 명사)만을 의미함
        :param text: 분석할 문장
        :return: 분석 결과 (예시 : ['사과', '바나나'])
        """
        result_nouns: List[str] = []
        nouns_list = self._kiwi.analyze(text)
        for form, tag, start, end in nouns_list[0][0]:
            if tag == 'NNG' or tag == 'NNP':
                result_nouns.append(form)
        return result_nouns

    def get_sentences(self, text: str) -> List[str]:
        """
        뮨장 추출
        :param text: 분석할 글
        :return: 추출된 문장
        """
        result_sentences: List[str] = []
        for sentence in self._kiwi.split_into_sents(text=text, return_tokens=True):
            token_list = sentence.tokens
            token_list_length = len(token_list)
            last_token = token_list[token_list_length - 1]
            before_last_token = token_list[token_list_length - 2]
            if (last_token.tag == 'EF' or last_token.tag == 'SF') and not (
                    before_last_token.tag == 'NNG' or before_last_token.tag == 'NNP'):
                result_sentences.append(sentence.text)
        return result_sentences
