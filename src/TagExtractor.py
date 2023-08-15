import re

from .KeywordExtractor import KeywordList, KeywordExtractor
from .MorphemeAnalyzer import MorphemeAnalyzer
from .SimilarityComparator import SimilarityComparator
from .NamedEntityRecognizer import NamedEntityRecognizer


class TagExtractor:
    def __init__(self, tag_set: set[str], named_entity_recognizer: NamedEntityRecognizer = NamedEntityRecognizer(),
                 keyword_extractor: KeywordExtractor = KeywordExtractor(),
                 morpheme_analyzer: MorphemeAnalyzer = MorphemeAnalyzer(),
                 similarity_comparator: SimilarityComparator = SimilarityComparator()):
        self.tag_set = tag_set
        self.named_entity_recognizer = named_entity_recognizer
        self.keyword_extractor = keyword_extractor
        self.morpheme_analyzer = morpheme_analyzer
        self.similarity_comparator = similarity_comparator
        self.phone_number_regex = re.compile(
            '[0-9|공|영|일|이|삼|사|오|육|륙|칠|팔|구|하나|둘|셋|넷|다섯|여섯|일곱|여덣|아홉]{3}-?[0-9|공|영|일|이|삼|사|오|육|륙|칠|팔|구|하나|둘|셋|넷|다섯|여섯|일곱|여덣|아홉]{4}-?[0-9|공|영|일|이|삼|사|오|육|륙|칠|팔|구|하나|둘|셋|넷|다섯|여섯|일곱|여덣|아홉]{4}')
        self.ner_excluded_tag_set = {'DATE', 'TIME', 'PHONE_NUMBER', 'PERSON', 'QUANTITY', 'LOCATION', 'ORGANIZATION'}

    def set_tag_set(self, tag_set: set[str]):
        """
        기본 태그 목록 재설정
        :param tag_set:
        :return:
        """
        self.tag_set = tag_set

    def text_pretreatment(self, text: str) -> str:
        """
        한국어 혼용 휴대전화 번호와 사람 및 기관 이름, 날짜, 인터넷 용어 삭제
        :param text: 전처리할 대상
        :return:전처리 결과
        """
        # 불필요 공백 제거
        text = text.replace('  ', '')
        # 한국어 혼용 휴대전화 번호 제거
        text = self.phone_number_regex.sub('', text)
        # 이름, 날짜, 수량 표현 제거
        ner_text_list = [text for text, tag in self.named_entity_recognizer.analyze(text=text) if
                         tag not in self.ner_excluded_tag_set]
        text = ''.join(ner_text_list)
        # 인터넷 용어 제거
        remove_sw_text_list = [token for token in self.morpheme_analyzer.tokenize(text=text) if
                               not token.tag.startswith('W') and not token.tag == 'SW']
        text = self.morpheme_analyzer.join(remove_sw_text_list)
        return text

    def get_tags(self, title: str, post_text: str, return_keyword: bool = False, top_n: int = 5,
                 score_point: float = 0.5,
                 similarity_point: float = 0.7) -> tuple[list[str], list[tuple[str, float]]] | list[str]:
        """
        해당 게시글에 대해 태그 반환
        :param title:제목
        :param post_text:게시글 본문
        :param return_keyword:키워드 반환 유무
        :param top_n:태그 상위 n개 제한
        :param score_point:키워드 추출 필터링 기준점
        :param similarity_point:유사도 비교 필터링 기준점
        :return:결과 태그들
        """
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

        # 가중치가 임계점 이상인 요소 추출
        title_noun_keyword_list = self._noun_keyword_list_filter(noun_keyword_list=title_noun_keyword_list,
                                                                 score_point=score_point)
        post_text_noun_keyword_list = self._noun_keyword_list_filter(noun_keyword_list=post_text_noun_keyword_list,
                                                                     score_point=score_point)

        # 최종 태그 추출
        title_max_n = int(top_n / 2)
        result_tag_list = []
        self._get_tags(noun_keyword_list=title_noun_keyword_list, max_n=title_max_n,
                       similarity_point=similarity_point, result_tag_list=result_tag_list)
        post_text_max_n = top_n - len(result_tag_list)
        self._get_tags(noun_keyword_list=post_text_noun_keyword_list, max_n=post_text_max_n,
                       similarity_point=similarity_point, result_tag_list=result_tag_list)

        if return_keyword:
            return result_tag_list, title_noun_keyword_list + post_text_noun_keyword_list
        else:
            return result_tag_list

    def _keyword_to_noun(self, keyword_list: KeywordList) -> dict:
        """
        추출된 키워드들을 명사로 변환
        :param keyword_list: 추출된 키워드
        :return: 변환된 결과
        """
        result_dict = dict()
        for keyword in keyword_list.get_keywords():
            nouns = self.morpheme_analyzer.get_nouns(text=keyword.get_keyword())
            if len(nouns) > 0:
                score_per_noun = keyword.get_score() / len(nouns)
                for noun in nouns:
                    if noun in result_dict:
                        result_dict[noun] += score_per_noun
                    else:
                        result_dict[noun] = score_per_noun
        return result_dict

    def _noun_keyword_list_filter(self, noun_keyword_list: list[tuple[str, float]], score_point: float = 0.5) -> list[
        tuple[str, float]]:
        """
        추출된 키워드 필터링
        :param noun_keyword_list:추출된 키워드 배열
        :param score_point:키워드 가중치 기준점
        :return: 필터링 결과
        """
        result_noun_keyword_list = []
        for noun_keyword in noun_keyword_list:
            if noun_keyword[1] < score_point:
                break
            result_noun_keyword_list.append(noun_keyword)
        return result_noun_keyword_list

    def _get_tags(self, noun_keyword_list: list[tuple[str, float]], max_n: int, similarity_point: float,
                  result_tag_list: list[str]):
        """
        전처리된 결과값에 대한 태그 추출 (최종 태그 추출)
        :param noun_keyword_list:
        :param max_n:
        :param similarity_point:
        :param result_tag_list:
        :return:
        """
        index = 0
        count = 0
        while count < max_n and index < len(noun_keyword_list):
            max_similarity = similarity_point
            max_similarity_default_tag = None
            for default_tag in self.tag_set:
                similarity = self.similarity_comparator.get_similarity(word1=default_tag,
                                                                       word2=noun_keyword_list[index][0])
                if max_similarity < similarity:
                    max_similarity = similarity
                    max_similarity_default_tag = default_tag

            if max_similarity_default_tag is not None:
                result_tag_list.append(max_similarity_default_tag)
                count += 1
            index += 1
        return result_tag_list
