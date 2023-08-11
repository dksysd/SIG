from typing import Any

import pymysql

from src.MorphemeAnalyzer import MorphemeAnalyzer
from src.TagExtractor import TagExtractor


class DatabaseController:
    """
    <데이터베이스 설계>
    CREATE TABLE tag
    (
        id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        name VARBINARY(20) NOT NULL
    );

    CREATE TABLE post
    (
        id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        title       VARCHAR(255) NOT NULL,
        content     TEXT,
        author      VARCHAR(100) NOT NULL,
        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE keyword
    (
        id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(20) NOT NULL
    );

    CREATE TABLE tag_post
    (
        tag_id  INT UNSIGNED,
        post_id INT UNSIGNED,
        FOREIGN KEY (tag_id) REFERENCES tag (id),
        FOREIGN KEY (post_id) REFERENCES post (id)
    );

    CREATE TABLE keyword_post
    (
        post_id    INT UNSIGNED,
        keyword_id INT UNSIGNED,
        value      FLOAT,
        FOREIGN KEY (post_id) REFERENCES post (id),
        FOREIGN KEY (keyword_id) REFERENCES keyword (id)
    );
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
        connection.commit()
        connection.close()
        return result_list

    def get_tag_set(self):
        """
        :return: 데이터베이스에 기록되어 있는 기본 태그들
        """
        tag_set = set()
        for result in self._execute(sql='SELECT tag."name" FROM "tag"'):
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
            sql='SELECT post."title", post."content", post."author" FROM "post" WHERE post."id" = (%d)', args=post_id)
        title = self._none_check(text=result_list[0][0])
        post_text = self._none_check(text=result_list[0][1])
        author = self._none_check(text=result_list[0][2])
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
        keyword_id = self._execute(sql='SELECT keyword."id" FROM keyword WHERE keyword."name" = (%s)', args=keyword)[0][
            0]
        if keyword_id:
            self._execute(sql='INSERT INTO keyword_post (keyword_id, value, post_id) VALUES (%d, %f, %d)',
                          args=(keyword_id, value, post_id))
        else:
            self._execute(sql='INSERT INTO keyword (name) VALUES (%s)', args=keyword)
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
        tag_id = self._execute(sql='SELECT tag."id" FROM tag WHERE tag."name" = (%d)', args=tag)
        self._execute(sql='INSERT INTO tag_post (tag_id, post_id) VALUES (%d, %d)', args=(tag_id, post_id))

    def _none_check(self, text: str) -> str:
        """
        text가 None일 경우 공백 문자열 반환
        """
        return '' if text is None else text


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
