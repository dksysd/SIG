from typing import Any

import pymysql

from src.MorphemeAnalyzer import MorphemeAnalyzer
from src.TagExtractor import TagExtractor


class DatabaseController:
    """
    <데이터베이스 설계>
    테이블 명 : tag
    도메인 목록 : [ID, NAME]

    테이블 명 : tag_post
    도메인 목록 : [TAG_ID, POST_ID]

    테이블 명 : post
    도메인 목록 : [ID, TITLE, CONTENT, AUTHOR]

    테이블 명 : keyword_post
    도메인 목록 : [POST_ID, KEYWORD_ID, VALUE]

    테이블 명 : keyword
    도메인 목록 : [ID, NAME]
    """

    def __init__(self, user: str, password: str, host: str, db: str):
        self.user = user
        self.password = password
        self.host = host
        self.db = db

    def _execute(self, sql: str, args=None) -> tuple[tuple[Any, ...], ...]:
        """
        SQL 쿼리 실행
        :return: 결과값
        """
        connection = pymysql.connect(user=self.user, password=self.password, host=self.host, db=self.db,
                                     charset='utf8')
        cursor = connection.cursor()
        cursor.execute(query=sql, args=args)
        result_list = cursor.fetchall()
        connection.commit()  # 그냥 해도 되나 몰겠다
        connection.close()
        return result_list

    def get_tag_set(self):
        """
        :return: 데이터베이스에 기록되어 있는 기본 태그들
        """
        tag_set = set()
        for result in self._execute(sql='SELECT tag."KEYWORD" FROM "tag"'):
            tag = result[0]
            tag_set.add(tag)
        return tag_set

    def get_data(self, post_id: int) -> tuple[str, str, str]:
        """
        post_number에 해당하는 정보 반환
        :param post_id: 게시글 번호
        :return: 정보 (제목, 작성자, 게시글)
        """
        result_list = self._execute(
            sql='SELECT post."TITLE", post."CONTENT", post."AUTHOR" FROM "post" WHERE post."ID" = (?)', args=post_id)
        title = result_list[0][0]
        post_text = result_list[0][1]
        author = result_list[0][2]
        return title, post_text, author

    def save_keywords(self, post_id: int, keyword_list: list[str, float]):
        """
        모든 키워드들 저장
        :param post_id: 해당하는 게시글 번호
        """
        for keyword, value in keyword_list:
            self.save_keyword(post_id=post_id, keyword=keyword, value=value)

    def save_keyword(self, post_id: int, keyword: str, value: float):
        """
        저장되지 않은 키워드의 경우, 키워드를 추가함. 이후 keyword_post 테이블에 해당 키워드와 게시글 관련 정보를 저장함.
        :param post_id: 해당하는 게시글 번호
        :param keyword: 키워드
        :param value: 키워드 가중치
        """
        keyword_id = self._execute(sql='SELECT keyword."ID" FROM keyword WHERE keyword."NAME" = (?)', args=keyword)[0][
            0]
        if keyword_id:
            self._execute(sql='INSERT INTO keyword_post (KEYWORD_ID, KEYWORD_VALUE, POST_ID) VALUES (?, ?, ?)',
                          args=(keyword_id, value, post_id))
        else:
            self._execute(sql='INSERT INTO keyword (NAME) VALUES (?)', args=keyword)
            self.save_keyword(post_id=post_id, keyword=keyword, value=value)

    def save_tags(self, post_id: int, tag_list: list[str]):
        """
        모든 태그들 저장
        :param post_id: 해당하는 게시글 번호
        :return:
        """
        for tag in tag_list:
            self.save_tag(post_id=post_id, tag=tag)

    def save_tag(self, post_id: int, tag: str):
        """
        tag의 ID를 획득하고, 이와 게시글 관련 정보를 tag_post 테이블에 저장
        :param post_id: 해당하는 게시글 번호
        :return:
        """
        tag_id = self._execute(sql='SELECT tag."ID" FROM tag WHERE tag."NAME" = (?)', args=tag)
        self._execute(sql='INSERT INTO tag_post (TAG_ID, POST_ID) VALUES (?, ?)', args=(tag_id, post_id))


class SETagExtractor:
    def __init__(self, user: str, password: str, host: str, db: str):
        self.database_controller = DatabaseController(user=user, password=password, host=host, db=db)
        tag_set = self.database_controller.get_tag_set()
        morpheme_analyzer = MorphemeAnalyzer()
        for tag in tag_set:
            morpheme_analyzer.add_user_word(word=tag)
        self.tag_extractor = TagExtractor(tag_set=tag_set, morpheme_analyzer=MorphemeAnalyzer(is_typos=True))

    def get_tags(self, post_id: int) -> list[str]:
        """
        게시글에 대한 키워드와 태그를 저장 및 반환
        :param post_id: 게시글 id
        :return: 게시글에 달린 태그
        """
        title, post_text, author = self.database_controller.get_data(post_id=post_id)
        tag_list, keyword_list = self.tag_extractor.get_tags(title=title, post_text=post_text, return_keyword=True)
        self.database_controller.save_keywords(post_id=post_id, keyword_list=keyword_list)
        self.database_controller.save_tags(post_id=post_id, tag_list=tag_list)
        return tag_list
