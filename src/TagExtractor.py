from KeywordExtractor import KeywordList, KeywordExtractor
from MorphemeAnalyzer import MorphemeAnalyzer
from SimilarityComparator import SimilarityComparator

import re
from typing import Union, Set


class TagExtractor:
    def __init__(self, tag_set: Set[str],
                 keyword_extractor: type[KeywordExtractor] = KeywordExtractor(),
                 morpheme_analyzer: type[MorphemeAnalyzer] = MorphemeAnalyzer(),
                 similarity_comparator: type[SimilarityComparator] = SimilarityComparator()):
        self.tag_set = tag_set
        self.keyword_extractor = keyword_extractor
        self.morpheme_analyzer = morpheme_analyzer
        self.similarity_comparator = similarity_comparator
        self.phone_number_regex = re.compile(
            '[0-9|공|영|일|이|삼|사|오|육|륙|칠|팔|구|하나|둘|셋|넷|다섯|여섯|일곱|여덣|아홉]{3}-?[0-9|공|영|일|이|삼|사|오|육|륙|칠|팔|구|하나|둘|셋|넷|다섯|여섯|일곱|여덣|아홉]{4}-?[0-9|공|영|일|이|삼|사|오|육|륙|칠|팔|구|하나|둘|셋|넷|다섯|여섯|일곱|여덣|아홉]{4}')

    def text_pretreatment(self, text: str) -> str:
        result_text = ''
        # 한국어 혼용 휴대전화 번호 제거
        text = self.phone_number_regex.sub('', text)
        # 이름, 날짜 제거
        # 인터넷 용어 제거
        for token in self.morpheme_analyzer.analyze(text=text):
            if not token.tag.startswith('W'):
                result_text += token.form
        return result_text

    def get_tags(self, title: str, post_text: str, save_keyword: bool = False, top_n: int = 5,
                 similarity_point: float = 0.5) -> Union[list[list[tuple[str, float]], list[str]], list[str]]:
        # 전처리
        pretreatment_title = self.text_pretreatment(title)
        pretreatment_post_text = self.text_pretreatment(post_text)

        # 문장 추출
        pretreatment_post_text_sentence_list = self.morpheme_analyzer.get_sentences(text=pretreatment_post_text)
        pretreatment_post_text = ' '.join(pretreatment_post_text_sentence_list)

        # 키워드 추출
        title_KeywordList = self.keyword_extractor.get_keywords(text=pretreatment_title)
        post_text_KeywordList = self.keyword_extractor.get_keywords(text=pretreatment_post_text)

        # 키워드 단어 명사화 및 동일 명사 가중치 합 연산
        title_noun_keyword_dict = self._keyword_to_noun(keyword_list=title_KeywordList)
        post_text_noun_keyword_dict = self._keyword_to_noun(keyword_list=post_text_KeywordList)

        # 가중치를 기준으로 정렬
        title_noun_keyword_list = sorted(title_noun_keyword_dict.items(), key=lambda item: item[1], reverse=True)
        post_text_noun_keyword_list = sorted(post_text_noun_keyword_dict.items(), key=lambda item: item[1],
                                             reverse=True)
        # 최종 태그 추출
        title_max_n = int(top_n / 2)
        title_result_tag_list = self._get_tags(noun_keyword_list=title_noun_keyword_list, max_n=title_max_n,
                                               similarity_point=similarity_point)
        post_text_max_n = top_n - len(title_result_tag_list)
        post_text_result_tag_list = self._get_tags(noun_keyword_list=post_text_noun_keyword_list, max_n=post_text_max_n,
                                                   similarity_point=similarity_point)
        result_tag_list = title_result_tag_list + post_text_result_tag_list

        if save_keyword:
            return [title_noun_keyword_list + post_text_noun_keyword_list, result_tag_list]
        else:
            return result_tag_list

    def _keyword_to_noun(self, keyword_list: KeywordList) -> dict:
        result_dict = dict()
        for keyword in keyword_list.get_keywords():
            nouns = self.morpheme_analyzer.get_nouns(text=keyword)
            score_per_noun = keyword.get_score() / len(nouns)
            for noun in nouns:
                result_dict[noun] += score_per_noun  # 작동 여부 확신 불가능 (파이썬 문법 숙련도 부족)
        return result_dict

    def _get_tags(self, noun_keyword_list: list[tuple[str, float]], max_n: int, similarity_point: float) -> list[str]:
        result_tag_list = []
        index = 0
        while index < max_n and index < len(noun_keyword_list):
            max_similarity_point = similarity_point
            max_point_default_tag = None
            for default_tag in self.tag_set:
                similarity_point = self.similarity_comparator.get_similarity(word1=default_tag,
                                                                             word2=noun_keyword_list[index][0])
                if max_similarity_point < similarity_point:
                    max_similarity_point = similarity_point
                    max_point_default_tag = default_tag
            result_tag_list.append(max_point_default_tag)
        return result_tag_list
